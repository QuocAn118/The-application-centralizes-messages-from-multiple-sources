"""Repository từ khoá dùng SQLAlchemy."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.keyword.domain.entities.keyword import Keyword
from src.modules.keyword.infrastructure.mappers.keyword_mapper import KeywordMapper
from src.modules.keyword.infrastructure.models.keyword_model import KeywordModel


class SqlAlchemyKeywordRepository:
    """Truy xuất từ khoá từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lay_model(self, keyword_id: UUID) -> KeywordModel | None:
        ket_qua = await self._session.execute(
            select(KeywordModel).where(KeywordModel.id == keyword_id)
        )
        return ket_qua.scalar_one_or_none()

    async def get_by_id(self, keyword_id: UUID) -> Keyword | None:
        model = await self._lay_model(keyword_id)
        return KeywordMapper.to_domain(model) if model else None

    async def get_by_normalized(self, department_id: UUID, normalized: str) -> Keyword | None:
        ket_qua = await self._session.execute(
            select(KeywordModel).where(
                KeywordModel.department_id == department_id,
                KeywordModel.normalized == normalized,
            )
        )
        model = ket_qua.scalar_one_or_none()
        return KeywordMapper.to_domain(model) if model else None

    async def add(self, keyword: Keyword) -> None:
        self._session.add(KeywordMapper.to_model(keyword))

    async def update(self, keyword: Keyword) -> None:
        model = await self._lay_model(keyword.id)
        if model is None:
            raise ValueError(f"Không tìm thấy từ khoá {keyword.id} để cập nhật.")
        KeywordMapper.update_model(model, keyword)

    async def delete(self, keyword_id: UUID) -> None:
        await self._session.execute(delete(KeywordModel).where(KeywordModel.id == keyword_id))

    async def list_for_departments(self, department_ids: list[UUID] | None) -> list[Keyword]:
        if department_ids is not None and not department_ids:
            return []

        cau = select(KeywordModel)
        if department_ids is not None:
            cau = cau.where(KeywordModel.department_id.in_(department_ids))
        cau = cau.order_by(KeywordModel.department_id, KeywordModel.created_at)
        ket_qua = await self._session.execute(cau)
        return [KeywordMapper.to_domain(m) for m in ket_qua.scalars()]

    async def list_all_active(self) -> list[Keyword]:
        cau = select(KeywordModel).order_by(KeywordModel.department_id, KeywordModel.created_at)
        ket_qua = await self._session.execute(cau)
        return [KeywordMapper.to_domain(m) for m in ket_qua.scalars()]
