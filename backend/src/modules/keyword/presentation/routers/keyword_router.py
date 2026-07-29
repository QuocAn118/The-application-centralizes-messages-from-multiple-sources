"""Endpoint CRUD từ khoá (Manager phòng mình / Admin)."""

from uuid import UUID

from fastapi import APIRouter

from src.modules.keyword.application.use_cases.keyword_use_cases import (
    CreateKeyword,
    DeleteKeyword,
    ListKeywords,
    UpdateKeyword,
)
from src.modules.keyword.infrastructure.repositories.keyword_repository import (
    SqlAlchemyKeywordRepository,
)
from src.modules.keyword.presentation.dependencies import (
    Actor,
    Clock,
    DbSession,
    Directory,
)
from src.modules.keyword.presentation.schemas.keyword_schemas import (
    CreateKeywordRequest,
    KeywordResponse,
    UpdateKeywordRequest,
)

router = APIRouter(tags=["keywords"])


@router.get("/keywords", response_model=list[KeywordResponse])
async def liet_ke_tu_khoa(actor: Actor, session: DbSession) -> list[KeywordResponse]:
    ds = await ListKeywords(SqlAlchemyKeywordRepository(session)).execute(actor)
    return [KeywordResponse.from_view(v) for v in ds]


@router.post("/keywords", response_model=KeywordResponse, status_code=201)
async def tao_tu_khoa(
    du_lieu: CreateKeywordRequest,
    actor: Actor,
    session: DbSession,
    directory: Directory,
    clock: Clock,
) -> KeywordResponse:
    v = await CreateKeyword(SqlAlchemyKeywordRepository(session), directory, clock).execute(
        actor, department_id=du_lieu.department_id, text=du_lieu.text
    )
    return KeywordResponse.from_view(v)


@router.patch("/keywords/{keyword_id}", response_model=KeywordResponse)
async def cap_nhat_tu_khoa(
    keyword_id: UUID,
    du_lieu: UpdateKeywordRequest,
    actor: Actor,
    session: DbSession,
    clock: Clock,
) -> KeywordResponse:
    v = await UpdateKeyword(SqlAlchemyKeywordRepository(session), clock).execute(
        actor, keyword_id=keyword_id, text=du_lieu.text
    )
    return KeywordResponse.from_view(v)


@router.delete("/keywords/{keyword_id}", status_code=204)
async def xoa_tu_khoa(keyword_id: UUID, actor: Actor, session: DbSession) -> None:
    await DeleteKeyword(SqlAlchemyKeywordRepository(session)).execute(actor, keyword_id)
