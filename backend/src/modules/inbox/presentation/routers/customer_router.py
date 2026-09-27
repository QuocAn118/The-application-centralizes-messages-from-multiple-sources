"""Endpoint panel khách (2b): ghi chú nội bộ theo phòng (BE-5)."""

from uuid import UUID

from fastapi import APIRouter, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.application.use_cases.customer_notes import CustomerNotes
from src.modules.inbox.domain.ports import IWorkforceDirectory
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.inbox.infrastructure.repositories.customer_note_repository import (
    SqlAlchemyCustomerNoteRepository,
)
from src.modules.inbox.presentation.dependencies import Actor, Clock, DbSession, Directory
from src.modules.inbox.presentation.schemas.customer_schemas import NoteRequest, NoteResponse
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
