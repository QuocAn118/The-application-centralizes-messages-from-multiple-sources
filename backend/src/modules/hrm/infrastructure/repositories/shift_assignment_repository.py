"""Repository buổi phân ca dùng SQLAlchemy."""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.hrm.domain.entities.shift_assignment import (
    ShiftAssignment,
    ShiftAssignmentStatus,
)
from src.modules.hrm.infrastructure.mappers.shift_assignment_mapper import (
    ShiftAssignmentMapper,
)
from src.modules.hrm.infrastructure.models.shift_assignment_model import (
    ShiftAssignmentModel,
)


class SqlAlchemyShiftAssignmentRepository:
    """Truy xuất buổi phân ca từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lay_model(self, assignment_id: UUID) -> ShiftAssignmentModel | None:
        ket_qua = await self._session.execute(
            select(ShiftAssignmentModel).where(ShiftAssignmentModel.id == assignment_id)
        )
        return ket_qua.scalar_one_or_none()

    async def get_by_id(self, assignment_id: UUID) -> ShiftAssignment | None:
        model = await self._lay_model(assignment_id)
        return ShiftAssignmentMapper.to_domain(model) if model else None

    async def add(self, assignment: ShiftAssignment) -> None:
        self._session.add(ShiftAssignmentMapper.to_model(assignment))

    async def update(self, assignment: ShiftAssignment) -> None:
        model = await self._lay_model(assignment.id)
        if model is None:
            raise ValueError(f"Không tìm thấy buổi phân ca {assignment.id} để cập nhật.")
        ShiftAssignmentMapper.update_model(model, assignment)

    async def list_active_for_user_on_date(
        self, user_id: UUID, work_date: date
    ) -> list[ShiftAssignment]:
        ket_qua = await self._session.execute(
            select(ShiftAssignmentModel).where(
                ShiftAssignmentModel.user_id == user_id,
                ShiftAssignmentModel.work_date == work_date,
                ShiftAssignmentModel.status == ShiftAssignmentStatus.ACTIVE,
            )
        )
        return [ShiftAssignmentMapper.to_domain(m) for m in ket_qua.scalars()]

    async def list_for_scope(
        self,
        user_ids: list[UUID] | None,
        department_ids: list[UUID] | None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ShiftAssignment]:
        # Danh sách rỗng nghĩa là không phạm vi nào — trả rỗng.
        if user_ids is not None and not user_ids:
            return []
        if department_ids is not None and not department_ids:
            return []

        cau = select(ShiftAssignmentModel)
        if user_ids is not None:
            cau = cau.where(ShiftAssignmentModel.user_id.in_(user_ids))
        if department_ids is not None:
            cau = cau.where(ShiftAssignmentModel.department_id.in_(department_ids))
        if date_from is not None:
            cau = cau.where(ShiftAssignmentModel.work_date >= date_from)
        if date_to is not None:
            cau = cau.where(ShiftAssignmentModel.work_date <= date_to)
        cau = cau.order_by(ShiftAssignmentModel.work_date, ShiftAssignmentModel.start_time)
        ket_qua = await self._session.execute(cau)
        return [ShiftAssignmentMapper.to_domain(m) for m in ket_qua.scalars()]
