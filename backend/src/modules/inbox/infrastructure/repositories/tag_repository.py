"""Implementation ``ITagRepository`` trên PostgreSQL (BE-6)."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.tag import Tag
from src.modules.inbox.infrastructure.models.tag_model import CustomerTagModel, TagModel


def _ve(m: TagModel) -> Tag:
    return Tag(id=m.id, name=m.name, color=m.color, is_active=m.is_active, created_at=m.created_at)


class SqlAlchemyTagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, tag: Tag) -> None:
        self._session.add(
            TagModel(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                is_active=tag.is_active,
                created_at=tag.created_at,
            )
        )

    async def update(self, tag: Tag) -> None:
        m = await self._session.get(TagModel, tag.id)
        if m is not None:
            m.name, m.color, m.is_active = tag.name, tag.color, tag.is_active

    async def get_by_id(self, tag_id: UUID) -> Tag | None:
        m = await self._session.get(TagModel, tag_id)
        return _ve(m) if m else None

    async def get_many(self, tag_ids: list[UUID]) -> list[Tag]:
        if not tag_ids:
            return []
        cau = select(TagModel).where(TagModel.id.in_(set(tag_ids)))
        return [_ve(m) for m in (await self._session.execute(cau)).scalars()]

    async def find_by_name(self, name: str) -> Tag | None:
        cau = select(TagModel).where(func.lower(TagModel.name) == name.lower())
        m = (await self._session.execute(cau)).scalar_one_or_none()
        return _ve(m) if m else None

    async def list_all(self, include_inactive: bool) -> list[Tag]:
        cau = select(TagModel).order_by(func.lower(TagModel.name))
        if not include_inactive:
            cau = cau.where(TagModel.is_active.is_(True))
        return [_ve(m) for m in (await self._session.execute(cau)).scalars()]

    async def list_for_customer(self, customer_id: UUID) -> list[Tag]:
        cau = (
            select(TagModel)
            .join(CustomerTagModel, CustomerTagModel.tag_id == TagModel.id)
            .where(CustomerTagModel.customer_id == customer_id)
            .order_by(func.lower(TagModel.name))
        )
        return [_ve(m) for m in (await self._session.execute(cau)).scalars()]

    async def set_for_customer(self, customer_id: UUID, tag_ids: list[UUID]) -> None:
        await self._session.execute(
            delete(CustomerTagModel).where(CustomerTagModel.customer_id == customer_id)
        )
        self._session.add_all(
            CustomerTagModel(customer_id=customer_id, tag_id=t) for t in dict.fromkeys(tag_ids)
        )
