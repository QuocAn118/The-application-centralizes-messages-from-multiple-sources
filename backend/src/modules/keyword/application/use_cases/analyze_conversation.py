"""Use case lõi #2: phân tích nhu cầu một hội thoại và tự phân về phòng.

Chạy SAU khi tin đã lưu (webhook router gọi, tách lỗi). Điều kiện: hội thoại
đang CHO_PHAN và có đủ tin của khách. Gọi LLM trích nhu cầu → khớp danh mục
keyword các phòng → nếu khớp đúng một phòng đủ tin cậy thì tự phân (qua
IConversationRouter gọi use case phân của #1); mơ hồ thì giữ CHO_PHAN. Mọi lỗi
LLM bị nuốt: log + trả kết quả "không phân tích được", KHÔNG ném lên trên — nhận
tin không được hỏng vì phân tích lỗi.
"""

import logging
from decimal import Decimal
from uuid import UUID

from src.modules.keyword.application.dto.keyword_dto import (
    AnalysisView,
    ExtractedTermView,
)
from src.modules.keyword.application.services.keyword_matcher import match_department
from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)
from src.modules.keyword.domain.ports import (
    ExtractorError,
    IConversationDirectory,
    IConversationRouter,
    IKeywordExtractor,
)
from src.modules.keyword.domain.repositories.analysis_repository import (
    IAnalysisRepository,
)
from src.modules.keyword.domain.repositories.keyword_repository import IKeywordRepository
from src.shared.application.ports import IClock

logger = logging.getLogger(__name__)

# Ngưỡng độ tin cậy tối thiểu của LLM để được tự phân (không phân bừa khi LLM
# tự đánh giá thấp). Đọc N tin đầu của khách.
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
    """Phân tích một hội thoại và tự phân nếu suy ra được phòng rõ ràng."""

    def __init__(
        self,
        keyword_repo: IKeywordRepository,
        analysis_repo: IAnalysisRepository,
        conversation_directory: IConversationDirectory,
        extractor: IKeywordExtractor,
        router: IConversationRouter,
        clock: IClock,
        confidence_threshold: Decimal = DEFAULT_CONFIDENCE_THRESHOLD,
        max_messages: int = DEFAULT_MAX_MESSAGES,
    ) -> None:
        self._keyword_repo = keyword_repo
        self._analysis_repo = analysis_repo
        self._conversation_directory = conversation_directory
        self._extractor = extractor
        self._router = router
        self._clock = clock
        self._threshold = confidence_threshold
        self._max_messages = max_messages

    async def execute(self, conversation_id: UUID) -> AnalysisView | None:
        """Phân tích một hội thoại. Trả ``None`` nếu bỏ qua (không phải CHO_PHAN
        / không có tin); ngược lại luôn trả một ``AnalysisView`` (kể cả khi LLM
        lỗi — outcome NOT_ANALYZED). Không bao giờ ném lỗi phân tích ra ngoài.
        """
        snapshot = await self._conversation_directory.get_snapshot(
            conversation_id, self._max_messages
        )
        # Chỉ phân tích hội thoại đang chờ phân và có ít nhất một tin của khách.
        if snapshot is None or not snapshot.is_awaiting or not snapshot.first_texts:
            return None

        now = self._clock.now()

        try:
            result = await self._extractor.extract(snapshot.first_texts)
        except ExtractorError:
            logger.exception(
                "Trích keyword thất bại — bỏ qua, tin vẫn nguyên",
                extra={"conversation_id": str(conversation_id)},
            )
            analysis = ConversationAnalysis.not_analyzed(conversation_id, now)
            await self._analysis_repo.add(analysis)
            return _view(analysis)

        if not result.terms:
            # LLM không trích được nhu cầu nào — coi như chưa phân tích được.
            analysis = ConversationAnalysis.not_analyzed(conversation_id, now)
            await self._analysis_repo.add(analysis)
            return _view(analysis)

        keywords = await self._keyword_repo.list_all_active()
        match = match_department(result.terms, keywords)

        du_tin_cay = result.confidence >= self._threshold
        if match.department_id is not None and du_tin_cay:
            phan_duoc = await self._router.assign_to_department(
                conversation_id, match.department_id
            )
            if phan_duoc:
                analysis = ConversationAnalysis.auto_assigned(
                    conversation_id=conversation_id,
                    extracted_terms=result.terms,
                    department_id=match.department_id,
                    confidence=result.confidence,
                    now=now,
                )
                await self._analysis_repo.add(analysis)
                return _view(analysis)

        # Khớp mơ hồ, tin cậy thấp, hoặc phân thất bại -> giữ CHO_PHAN, vẫn lưu
        # cụm nhu cầu để Manager tham khảo và #5 phát hiện nhu cầu mới.
        analysis = ConversationAnalysis.ambiguous(
            conversation_id=conversation_id,
            extracted_terms=result.terms,
            confidence=result.confidence,
            now=now,
        )
        await self._analysis_repo.add(analysis)
        return _view(analysis)
