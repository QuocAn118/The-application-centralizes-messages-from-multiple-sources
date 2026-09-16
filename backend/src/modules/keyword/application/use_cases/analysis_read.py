"""Use case đọc kết quả phân tích hội thoại theo phạm vi quyền."""

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
from src.modules.keyword.domain.repositories.analysis_repository import (
    IAnalysisRepository,
)
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
    """Liệt kê phân tích theo phạm vi phòng đề xuất của người gọi.

    Admin: tất cả. Manager/Staff: phòng mình (theo ``suggested_department_id``).
    """

    def __init__(self, analysis_repo: IAnalysisRepository) -> None:
        self._analysis_repo = analysis_repo

    async def execute(
        self, actor: KeywordActor, limit: int = 50, offset: int = 0
    ) -> Page[AnalysisView]:
        department_ids = pham_vi_phong_doc(actor)
        items = await self._analysis_repo.list_for_departments(department_ids, limit, offset)
        total = await self._analysis_repo.count_for_departments(department_ids)
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
    """Gác phạm vi cho việc **kích hoạt phân tích lại** (nợ N5).

    Trước đây ``POST /conversations/{id}/analyses`` chỉ kiểm vai Manager/Admin,
    không kiểm phòng — trong khi ``GET`` cùng đường dẫn đó lại kiểm. Đo thật:
    một Manager **GET** phân tích của hội thoại phòng khác nhận **403**, nhưng
    **POST** kích hoạt lại chính hội thoại đó nhận **200**. Đường GHI dễ hơn
    đường ĐỌC là ngược đời, và ghi ở đây nghĩa là gọi LLM (tốn tiền) rồi có thể
    định tuyến lại hội thoại của phòng khác.

    Quy tắc, cố ý khớp với ``GetConversationAnalyses``:

    - Admin: mọi hội thoại.
    - Manager: hội thoại **đã có** bản ghi phân tích đề xuất về phòng mình.
    - Hội thoại **chưa có bản ghi nào**: cho qua. ``CHO_PHAN`` nghĩa là chưa
      thuộc phòng nào (``status`` suy ra từ ``department_id`` ở #1), nên không
      có phòng để mà xâm phạm — đây chính là trường hợp dùng chính đáng: Manager
      vừa thêm từ khoá và muốn AI thử phân lại hàng chờ chung.

    Nói cách khác: chặn việc *đụng vào hội thoại của phòng khác*, không chặn
    việc *giúp phân hàng chờ chưa của ai*.
    """

    def __init__(self, analysis_repo: IAnalysisRepository) -> None:
        self._analysis_repo = analysis_repo

    async def execute(self, actor: KeywordActor, conversation_id: UUID) -> None:
        if actor.role is ActorRole.ADMIN:
            return

        items = await self._analysis_repo.list_for_conversation(conversation_id)
        if not items:
            # Chưa phân tích lần nào -> chưa thuộc phòng nào -> ai cũng giúp được.
            return

        if any(a.suggested_department_id == actor.department_id for a in items):
            return

        raise PermissionDeniedError(
            "Bạn không có quyền phân tích lại hội thoại của phòng khác.",
            code="ANALYSIS_FORBIDDEN",
        )
