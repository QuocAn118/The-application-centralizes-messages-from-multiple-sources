"""Repository mục tiêu KPI dùng SQLAlchemy."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.hrm.domain.entities.kpi_target import KpiTarget
from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.modules.hrm.infrastructure.mappers.kpi_target_mapper import KpiTargetMapper
from src.modules.hrm.infrastructure.models.kpi_target_model import KpiTargetModel


class SqlAlchemyKpiTargetRepository:
    """Truy xuất mục tiêu KPI từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lay_model(self, target_id: UUID) -> KpiTargetModel | None:
        ket_qua = await self._session.execute(
            select(KpiTargetModel).where(KpiTargetModel.id == target_id)
        )
        return ket_qua.scalar_one_or_none()

    async def get_by_id(self, target_id: UUID) -> KpiTarget | None:
        model = await self._lay_model(target_id)
        return KpiTargetMapper.to_domain(model) if model else None

    async def get_for(
        self,
        subject_type: KpiSubjectType,
        subject_id: UUID,
        metric_type: KpiMetricType,
        period: KpiPeriod,
    ) -> KpiTarget | None:
        ket_qua = await self._session.execute(
            select(KpiTargetModel).where(
                KpiTargetModel.subject_type == subject_type.value,
                KpiTargetModel.subject_id == subject_id,
                KpiTargetModel.metric_type == metric_type.value,
                KpiTargetModel.period_year == period.year,
                KpiTargetModel.period_month == period.month,
            )
        )
        model = ket_qua.scalar_one_or_none()
        return KpiTargetMapper.to_domain(model) if model else None

    async def add(self, target: KpiTarget) -> None:
        self._session.add(KpiTargetMapper.to_model(target))

    async def update(self, target: KpiTarget) -> None:
        model = await self._lay_model(target.id)
        if model is None:
            raise ValueError(f"Không tìm thấy mục tiêu KPI {target.id} để cập nhật.")
        KpiTargetMapper.update_model(model, target)

    async def list_in_scope(
        self,
        department_ids: list[UUID] | None,
        subject_id: UUID | None = None,
        period: KpiPeriod | None = None,
    ) -> list[KpiTarget]:
        if department_ids is not None and not department_ids:
            return []

        cau = select(KpiTargetModel)
        if department_ids is not None:
            cau = cau.where(KpiTargetModel.department_id.in_(department_ids))
        if subject_id is not None:
            cau = cau.where(KpiTargetModel.subject_id == subject_id)
        if period is not None:
            cau = cau.where(
                KpiTargetModel.period_year == period.year,
                KpiTargetModel.period_month == period.month,
            )
        cau = cau.order_by(KpiTargetModel.created_at)
        ket_qua = await self._session.execute(cau)
        return [KpiTargetMapper.to_domain(m) for m in ket_qua.scalars()]
