"""Implementation ``ICustomerNoteRepository`` trên PostgreSQL (BE-5)."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.customer_note import CustomerNote
from src.modules.inbox.infrastructure.models.customer_note_model import CustomerNoteModel


def _ve_entity(m: CustomerNoteModel) -> CustomerNote:
    return CustomerNote(
        id=m.id,
        customer_id=m.customer_id,
        department_id=m.department_id,
        author_id=m.author_id,
        body=m.body,
        created_at=m.created_at,
    )


class SqlAlchemyCustomerNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, note: CustomerNote) -> None:
        self._session.add(
            CustomerNoteModel(
                id=note.id,
                customer_id=note.customer_id,
                department_id=note.department_id,
                author_id=note.author_id,
                body=note.body,
                created_at=note.created_at,
            )
        )

    async def get_by_id(self, note_id: UUID) -> CustomerNote | None:
        m = await self._session.get(CustomerNoteModel, note_id)
        return _ve_entity(m) if m else None

    async def list_for_customer(
        self, customer_id: UUID, *, tat_ca_phong: bool, department_id: UUID | None
    ) -> list[CustomerNote]:
        cau = select(CustomerNoteModel).where(CustomerNoteModel.customer_id == customer_id)
        if not tat_ca_phong:
            cau = cau.where(
                CustomerNoteModel.department_id.is_(None)
                if department_id is None
                else CustomerNoteModel.department_id == department_id
            )
        cau = cau.order_by(CustomerNoteModel.created_at.desc(), CustomerNoteModel.id.desc())
        return [_ve_entity(m) for m in (await self._session.execute(cau)).scalars()]

    async def delete(self, note_id: UUID) -> None:
        await self._session.execute(
            delete(CustomerNoteModel).where(CustomerNoteModel.id == note_id)
        )
