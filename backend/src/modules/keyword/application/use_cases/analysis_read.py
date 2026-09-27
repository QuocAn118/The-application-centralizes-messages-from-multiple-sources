"""Use case đọc kết quả phân tích hội thoại theo phạm vi quyền."""

from collections.abc import Sequence
from uuid import UUID

from src.modules.keyword.application.actor import ActorRole, KeywordActor
from src.modules.keyword.application.authorization import pham_vi_phong_doc
from src.modules.keyword.application.dto.keyword_dto import (
    AnalysisView,
    ExtractedTermView,
    Page,
)
from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)
from src.modules.keyword.domain.ports import IConversationDirectory
from src.modules.keyword.domain.repositories.analysis_repository import (
    IAnalysisRepository,
)
from src.modules.keyword.domain.value_objects.extracted_term import AnalysisOutcome
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError


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


class ListConversationAnalyses:
    """Liệt kê phân tích theo phạm vi của người gọi (BE-10, 2026-09).

    - Admin: tất cả.
    - Manager: đề xuất về phòng mình **cộng** mọi hội thoại HIỆN đang chờ phân —
      nhất quán với quy tắc "phân tích lại" (Manager nào cũng cứu được hàng chờ
      chung). Trước đây AMBIGUOUS/NOT_ANALYZED luôn có phòng đề xuất ``null`` nên
      chỉ Admin thấy, tức đúng những hội thoại cần người nhất lại bị giấu.
    - Staff: đề xuất về phòng mình (Staff không thấy hàng chờ phân ở Hộp thư).

    ``outcomes`` lọc kết cục trên TOÀN BỘ dữ liệu (lọc "Cần xem lại" ở màn Phân
    tích AI) — lọc sau phân trang ở client chỉ lọc được một trang.
    """

    def __init__(self, analysis_repo: IAnalysisRepository) -> None:
        self._analysis_repo = analysis_repo

    async def execute(
        self,
        actor: KeywordActor,
        limit: int = 50,
        offset: int = 0,
        outcomes: Sequence[AnalysisOutcome] | None = None,
    ) -> Page[AnalysisView]:
        department_ids = pham_vi_phong_doc(actor)
        kem_cho_phan = actor.role is ActorRole.MANAGER
        items = await self._analysis_repo.list_for_departments(
            department_ids, limit, offset, kem_cho_phan=kem_cho_phan, outcomes=outcomes
        )
        total = await self._analysis_repo.count_for_departments(
            department_ids, kem_cho_phan=kem_cho_phan, outcomes=outcomes
        )
        return Page(items=[_view(a) for a in items], total=total, limit=limit, offset=offset)


class GetConversationAnalyses:
    """Lịch sử phân tích của một hội thoại.

    Phạm vi: Admin tất cả; Manager/Staff chỉ khi bản ghi thuộc phòng mình. Vì
    một hội thoại có thể nhiều bản ghi (mơ hồ rồi tự phân sau), cho xem nếu có ít
    nhất một bản ghi được đề xuất về phòng mình, hoặc là Admin.
    """

    def __init__(self, analysis_repo: IAnalysisRepository) -> None:
        self._analysis_repo = analysis_repo

    async def execute(self, actor: KeywordActor, conversation_id: UUID) -> list[AnalysisView]:
        items = await self._analysis_repo.list_for_conversation(conversation_id)
        if not items:
            raise NotFoundError(
                "Không tìm thấy phân tích cho hội thoại này.", code="ANALYSIS_NOT_FOUND"
            )

        if actor.role is not ActorRole.ADMIN:
            thuoc_phong_minh = any(a.suggested_department_id == actor.department_id for a in items)
            if not thuoc_phong_minh:
                raise PermissionDeniedError(
                    "Bạn không có quyền xem phân tích của hội thoại này.",
                    code="ANALYSIS_FORBIDDEN",
                )

        return [_view(a) for a in items]


class BaoDamKichHoatPhanTichDuoc:
    """Gác phạm vi cho việc **kích hoạt phân tích lại** (nợ N5, sửa lại 2026-09).

    Xét theo phòng **HIỆN TẠI** của hội thoại, không theo bản ghi phân tích:

    - Admin: mọi hội thoại.
    - Hội thoại chờ phân (chưa thuộc phòng nào): Manager nào cũng được — đây là
      trường hợp dùng chính đáng: AI lỗi / mơ hồ lúc đầu, Manager thêm từ khoá rồi
      cho phân tích lại hàng chờ chung.
    - Hội thoại đã thuộc phòng X: chỉ Manager phòng X.

    Bản trước (b82935a2) xét theo bản ghi phân tích nên chặn nhầm hội thoại chờ
    phân đã có bản ghi NOT_ANALYZED, hoặc AMBIGUOUS nghiêng về phòng khác.
    """

    def __init__(self, conversation_directory: IConversationDirectory) -> None:
        self._conversation_directory = conversation_directory

    async def execute(self, actor: KeywordActor, conversation_id: UUID) -> None:
        if actor.role is ActorRole.ADMIN:
            return

        snapshot = await self._conversation_directory.get_snapshot(conversation_id, 1)
        if snapshot is None or snapshot.department_id is None:
            # Không có / chờ phân -> chưa thuộc phòng nào -> ai cũng giúp được.
            return
        if snapshot.department_id == actor.department_id:
            return

        raise PermissionDeniedError(
            "Bạn không có quyền phân tích lại hội thoại của phòng khác.",
            code="ANALYSIS_FORBIDDEN",
        )
