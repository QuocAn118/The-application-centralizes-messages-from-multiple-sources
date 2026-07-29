"""Use case lõi #2: cho LLM phân loại một hội thoại và tự phân về phòng.

Chạy SAU khi tin đã lưu (webhook router gọi, tách lỗi). Điều kiện: hội thoại
đang CHO_PHAN và có đủ tin của khách. Gom danh mục từ khoá các phòng → cho LLM
đọc vài tin đầu và tự chọn phòng phù hợp → nếu phòng LLM chọn hợp lệ (tồn tại,
đang hoạt động) và đủ tin cậy thì tự phân (qua IConversationRouter gọi use case
phân của #1); ngược lại giữ CHO_PHAN. Mọi lỗi LLM bị nuốt: log + trả kết quả
"không phân tích được", KHÔNG ném lên trên — nhận tin không được hỏng.

Guard chống gọi LLM lặp: hội thoại đã có bản ghi phân tích thì bỏ qua (trừ khi
kích hoạt lại thủ công — dùng ``force``).
"""

import logging
from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from src.modules.keyword.application.dto.keyword_dto import (
    AnalysisView,
    ExtractedTermView,
)
from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)
from src.modules.keyword.domain.ports import (
    ClassifierError,
    IConversationClassifier,
    IConversationDirectory,
    IConversationRouter,
    IWorkforceDirectory,
)
from src.modules.keyword.domain.repositories.analysis_repository import (
    IAnalysisRepository,
)
from src.modules.keyword.domain.repositories.keyword_repository import IKeywordRepository
from src.modules.keyword.domain.value_objects.extracted_term import DepartmentKeywords
from src.shared.application.ports import IClock

logger = logging.getLogger(__name__)

# Ngưỡng độ tin cậy tối thiểu của LLM để được tự phân.
DEFAULT_CONFIDENCE_THRESHOLD = Decimal("0.5")
DEFAULT_MAX_MESSAGES = 3


def _view(a: ConversationAnalysis) -> AnalysisView:
    return AnalysisView(
        id=a.id,
        conversation_id=a.conversation_id,
        outcome=a.outcome,
        extracted_terms=tuple(
            ExtractedTermView(text=t.text, normalized=t.normalized) for t in a.extracted_terms
        ),
        created_at=a.created_at,
        suggested_department_id=a.suggested_department_id,
        confidence=a.confidence,
    )


class AnalyzeConversation:
    """Cho LLM phân loại một hội thoại và tự phân nếu chọn được phòng hợp lệ."""

    def __init__(
        self,
        keyword_repo: IKeywordRepository,
        analysis_repo: IAnalysisRepository,
        conversation_directory: IConversationDirectory,
        classifier: IConversationClassifier,
        router: IConversationRouter,
        workforce: IWorkforceDirectory,
        clock: IClock,
        confidence_threshold: Decimal = DEFAULT_CONFIDENCE_THRESHOLD,
        max_messages: int = DEFAULT_MAX_MESSAGES,
    ) -> None:
        self._keyword_repo = keyword_repo
        self._analysis_repo = analysis_repo
        self._conversation_directory = conversation_directory
        self._classifier = classifier
        self._router = router
        self._workforce = workforce
        self._clock = clock
        self._threshold = confidence_threshold
        self._max_messages = max_messages

    async def execute(self, conversation_id: UUID, force: bool = False) -> AnalysisView | None:
        """Phân tích một hội thoại. Trả ``None`` nếu bỏ qua (không phải CHO_PHAN /
        không có tin / đã phân tích rồi và không ``force``); ngược lại luôn trả một
        ``AnalysisView``. Không bao giờ ném lỗi phân tích ra ngoài.
        """
        snapshot = await self._conversation_directory.get_snapshot(
            conversation_id, self._max_messages
        )
        if snapshot is None or not snapshot.is_awaiting or not snapshot.first_texts:
            return None

        # Guard chống gọi LLM lặp: đã phân tích hội thoại này rồi thì thôi, trừ
        # khi Manager kích hoạt lại (force).
        if not force:
            da_co = await self._analysis_repo.list_for_conversation(conversation_id)
            if da_co:
                return None

        now = self._clock.now()
        departments = await self._danh_muc_theo_phong()

        try:
            result = await self._classifier.classify(snapshot.first_texts, departments)
        except ClassifierError:
            logger.exception(
                "Phân loại hội thoại thất bại — bỏ qua, tin vẫn nguyên",
                extra={"conversation_id": str(conversation_id)},
            )
            return await self._luu(ConversationAnalysis.not_analyzed(conversation_id, now))

        chon_duoc_phong = result.department_id is not None
        du_tin_cay = result.confidence >= self._threshold
        hop_le = chon_duoc_phong and await self._phong_hop_le(result.department_id)

        if hop_le and du_tin_cay:
            assert result.department_id is not None  # cho mypy: hợp_le đảm bảo
            if await self._router.assign_to_department(conversation_id, result.department_id):
                return await self._luu(
                    ConversationAnalysis.auto_assigned(
                        conversation_id=conversation_id,
                        extracted_terms=result.terms,
                        department_id=result.department_id,
                        confidence=result.confidence,
                        now=now,
                    )
                )

        # LLM không chọn được phòng / phòng không hợp lệ / tin cậy thấp / phân
        # thất bại -> giữ CHO_PHAN, vẫn lưu cụm nhu cầu cho Manager và #5.
        if result.terms:
            return await self._luu(
                ConversationAnalysis.ambiguous(
                    conversation_id=conversation_id,
                    extracted_terms=result.terms,
                    confidence=result.confidence,
                    now=now,
                )
            )
        return await self._luu(ConversationAnalysis.not_analyzed(conversation_id, now))

    async def _danh_muc_theo_phong(self) -> tuple[DepartmentKeywords, ...]:
        """Gom từ khoá theo phòng để bơm vào prompt LLM."""
        gom: dict[UUID, list[str]] = defaultdict(list)
        for kw in await self._keyword_repo.list_all_active():
            gom[kw.department_id].append(kw.text)
        return tuple(
            DepartmentKeywords(department_id=dept, keywords=tuple(kws)) for dept, kws in gom.items()
        )

    async def _phong_hop_le(self, department_id: UUID | None) -> bool:
        if department_id is None:
            return False
        return await self._workforce.department_exists_active(department_id)

    async def _luu(self, analysis: ConversationAnalysis) -> AnalysisView:
        await self._analysis_repo.add(analysis)
        return _view(analysis)
