"""Repository bản ghi phân tích hội thoại dùng SQLAlchemy."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)
from src.modules.keyword.infrastructure.mappers.conversation_analysis_mapper import (
    ConversationAnalysisMapper,
)
from src.modules.keyword.infrastructure.models.conversation_analysis_model import (
    ConversationAnalysisModel,
)


class SqlAlchemyAnalysisRepository:
    """Truy xuất bản ghi phân tích hội thoại từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, analysis_id: UUID) -> ConversationAnalysis | None:
        ket_qua = await self._session.execute(
            select(ConversationAnalysisModel).where(ConversationAnalysisModel.id == analysis_id)
        )
        model = ket_qua.scalar_one_or_none()
        return ConversationAnalysisMapper.to_domain(model) if model else None

    async def add(self, analysis: ConversationAnalysis) -> None:
        self._session.add(ConversationAnalysisMapper.to_model(analysis))

    async def list_for_conversation(self, conversation_id: UUID) -> list[ConversationAnalysis]:
        cau = (
            select(ConversationAnalysisModel)
            .where(ConversationAnalysisModel.conversation_id == conversation_id)
            .order_by(ConversationAnalysisModel.created_at.desc())
        )
        ket_qua = await self._session.execute(cau)
        return [ConversationAnalysisMapper.to_domain(m) for m in ket_qua.scalars()]

    async def list_for_departments(
        self, department_ids: list[UUID] | None, limit: int = 50, offset: int = 0
    ) -> list[ConversationAnalysis]:
        if department_ids is not None and not department_ids:
            return []

        cau = select(ConversationAnalysisModel)
        if department_ids is not None:
            cau = cau.where(ConversationAnalysisModel.suggested_department_id.in_(department_ids))
        cau = cau.order_by(ConversationAnalysisModel.created_at.desc()).limit(limit).offset(offset)
        ket_qua = await self._session.execute(cau)
        return [ConversationAnalysisMapper.to_domain(m) for m in ket_qua.scalars()]

    async def count_for_departments(self, department_ids: list[UUID] | None) -> int:
        if department_ids is not None and not department_ids:
            return 0

        cau = select(func.count()).select_from(ConversationAnalysisModel)
        if department_ids is not None:
            cau = cau.where(ConversationAnalysisModel.suggested_department_id.in_(department_ids))
        ket_qua = await self._session.execute(cau)
        return ket_qua.scalar_one()
