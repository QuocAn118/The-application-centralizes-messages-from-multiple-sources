"""Endpoint panel khách (2b): ghi chú theo phòng (BE-5) + nhãn dùng chung (BE-6)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.application.use_cases.customer_notes import CustomerNotes
from src.modules.inbox.application.use_cases.tags import Tags
from src.modules.inbox.domain.entities.tag import Tag
from src.modules.inbox.domain.ports import IWorkforceDirectory
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.inbox.infrastructure.repositories.customer_note_repository import (
    SqlAlchemyCustomerNoteRepository,
)
from src.modules.inbox.infrastructure.repositories.tag_repository import SqlAlchemyTagRepository
from src.modules.inbox.presentation.dependencies import Actor, Clock, DbSession, Directory
from src.modules.inbox.presentation.schemas.customer_schemas import (
    CustomerTagsRequest,
    NoteRequest,
    NoteResponse,
    TagCreateRequest,
    TagResponse,
    TagUpdateRequest,
)
from src.shared.application.ports import IClock

router = APIRouter(tags=["inbox"])


def _uc(session: AsyncSession, directory: IWorkforceDirectory, clock: IClock) -> CustomerNotes:
    return CustomerNotes(
        SqlAlchemyCustomerNoteRepository(session),
        SqlAlchemyConversationRepository(session),
        directory,
        clock,
    )


@router.get("/customers/{customer_id}/notes", response_model=list[NoteResponse])
async def xem_ghi_chu(
    customer_id: UUID, actor: Actor, session: DbSession, directory: Directory, clock: Clock
) -> list[NoteResponse]:
    ghi_chu = await _uc(session, directory, clock).xem(actor, customer_id)
    return [NoteResponse.from_view(g) for g in ghi_chu]


@router.post("/customers/{customer_id}/notes", response_model=NoteResponse, status_code=201)
async def viet_ghi_chu(
    customer_id: UUID,
    du_lieu: NoteRequest,
    actor: Actor,
    session: DbSession,
    directory: Directory,
    clock: Clock,
) -> NoteResponse:
    view = await _uc(session, directory, clock).viet(actor, customer_id, du_lieu.body)
    return NoteResponse.from_view(view)


@router.delete("/notes/{note_id}", status_code=204)
async def xoa_ghi_chu(
    note_id: UUID, actor: Actor, session: DbSession, directory: Directory, clock: Clock
) -> Response:
    await _uc(session, directory, clock).xoa(actor, note_id)
    return Response(status_code=204)


# ---- BE-6: nhãn -----------------------------------------------------------


def _tags(session: AsyncSession, clock: IClock) -> Tags:
    return Tags(SqlAlchemyTagRepository(session), SqlAlchemyConversationRepository(session), clock)


def _ra(t: Tag) -> TagResponse:
    return TagResponse(id=t.id, name=t.name, color=t.color, is_active=t.is_active)


@router.get("/tags", response_model=list[TagResponse])
async def danh_sach_nhan(
    actor: Actor,
    session: DbSession,
    clock: Clock,
    include_inactive: Annotated[bool, Query()] = False,
) -> list[TagResponse]:
    return [_ra(t) for t in await _tags(session, clock).danh_sach(actor, include_inactive)]


@router.post("/tags", response_model=TagResponse, status_code=201)
async def tao_nhan(
    du_lieu: TagCreateRequest, actor: Actor, session: DbSession, clock: Clock
) -> TagResponse:
    return _ra(await _tags(session, clock).tao(actor, du_lieu.name, du_lieu.color))


@router.patch("/tags/{tag_id}", response_model=TagResponse)
async def sua_nhan(
    tag_id: UUID, du_lieu: TagUpdateRequest, actor: Actor, session: DbSession, clock: Clock
) -> TagResponse:
    nhan = await _tags(session, clock).sua(
        actor, tag_id, du_lieu.name, du_lieu.color, du_lieu.is_active
    )
    return _ra(nhan)


@router.get("/customers/{customer_id}/tags", response_model=list[TagResponse])
async def nhan_cua_khach(
    customer_id: UUID, actor: Actor, session: DbSession, clock: Clock
) -> list[TagResponse]:
    return [_ra(t) for t in await _tags(session, clock).cua_khach(actor, customer_id)]


@router.put("/customers/{customer_id}/tags", response_model=list[TagResponse])
async def gan_nhan_cho_khach(
    customer_id: UUID,
    du_lieu: CustomerTagsRequest,
    actor: Actor,
    session: DbSession,
    clock: Clock,
) -> list[TagResponse]:
    ket_qua = await _tags(session, clock).gan_cho_khach(actor, customer_id, du_lieu.tag_ids)
    return [_ra(t) for t in ket_qua]
