"""Endpoint xem kết quả phân tích hội thoại + kích hoạt phân tích lại.

Phạm vi quyền: Admin tất cả; Manager/Staff theo phòng đề xuất. Kích hoạt lại
(``force``) cho Manager/Admin chạy lại LLM cho một hội thoại (ví dụ vừa thêm từ
khoá). Lỗi LLM được use case nuốt gọn, không nổi ra HTTP.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from src.modules.keyword.application.use_cases.analysis_read import (
    GetConversationAnalyses,
    ListConversationAnalyses,
)
from src.modules.keyword.infrastructure.repositories.analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from src.modules.keyword.presentation.dependencies import (
    Actor,
    DbSession,
    build_analyze_conversation,
)
from src.modules.keyword.presentation.schemas.keyword_schemas import (
    AnalysisPageResponse,
    AnalysisResponse,
)

router = APIRouter(tags=["analyses"])


@router.get("/analyses", response_model=AnalysisPageResponse)
async def liet_ke_phan_tich(
    actor: Actor,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AnalysisPageResponse:
    page = await ListConversationAnalyses(SqlAlchemyAnalysisRepository(session)).execute(
        actor, limit=limit, offset=offset
    )
    return AnalysisPageResponse.from_page(page)


@router.get(
    "/conversations/{conversation_id}/analyses",
    response_model=list[AnalysisResponse],
)
async def xem_phan_tich_hoi_thoai(
    conversation_id: UUID, actor: Actor, session: DbSession
) -> list[AnalysisResponse]:
    ds = await GetConversationAnalyses(SqlAlchemyAnalysisRepository(session)).execute(
        actor, conversation_id
    )
    return [AnalysisResponse.from_view(v) for v in ds]


@router.post(
    "/conversations/{conversation_id}/analyses",
    response_model=AnalysisResponse | None,
)
async def kich_hoat_phan_tich_lai(
    conversation_id: UUID,
    actor: Actor,
    session: DbSession,
    request: Request,
) -> AnalysisResponse | None:
    """Chạy lại phân tích cho một hội thoại (bỏ qua guard chưa-phân-tích).

    Chỉ Manager/Admin. Trả ``None`` (200) nếu hội thoại không đủ điều kiện phân
    tích (không CHO_PHAN / không có tin); ngược lại trả bản ghi phân tích mới.
    """
    from src.modules.keyword.application.authorization import bao_dam_quan_ly_hoac_admin

    bao_dam_quan_ly_hoac_admin(actor)
    use_case = build_analyze_conversation(request, session)
    view = await use_case.execute(conversation_id, force=True)
    return AnalysisResponse.from_view(view) if view is not None else None
