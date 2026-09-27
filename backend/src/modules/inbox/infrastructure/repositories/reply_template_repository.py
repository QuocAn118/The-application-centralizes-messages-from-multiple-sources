"""Implementation ``IReplyTemplateRepository`` trên PostgreSQL (BE-7)."""

from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.reply_template import ReplyTemplate
from src.modules.inbox.infrastructure.models.reply_template_model import ReplyTemplateModel


def _ve(m: ReplyTemplateModel) -> ReplyTemplate:
    return ReplyTemplate(
        id=m.id,
        department_id=m.department_id,
        title=m.title,
        body=m.body,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyReplyTemplateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, template: ReplyTemplate) -> None:
        self._session.add(ReplyTemplateModel(**template.__dict__))

    async def update(self, template: ReplyTemplate) -> None:
        m = await self._session.get(ReplyTemplateModel, template.id)
        if m is not None:
            m.title, m.body, m.updated_at = template.title, template.body, template.updated_at

    async def get_by_id(self, template_id: UUID) -> ReplyTemplate | None:
        m = await self._session.get(ReplyTemplateModel, template_id)
        return _ve(m) if m else None

    async def delete(self, template_id: UUID) -> None:
        await self._session.execute(
            delete(ReplyTemplateModel).where(ReplyTemplateModel.id == template_id)
        )

    async def list_visible(
        self, *, tat_ca: bool, department_id: UUID | None
    ) -> list[ReplyTemplate]:
        cau = select(ReplyTemplateModel)
        if not tat_ca:
            dk: list[ColumnElement[bool]] = [ReplyTemplateModel.department_id.is_(None)]
            if department_id is not None:
                dk.append(ReplyTemplateModel.department_id == department_id)
            cau = cau.where(or_(*dk))
        cau = cau.order_by(func.lower(ReplyTemplateModel.title))
        return [_ve(m) for m in (await self._session.execute(cau)).scalars()]
