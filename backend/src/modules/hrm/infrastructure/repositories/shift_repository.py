"""Repository mẫu ca dùng SQLAlchemy."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.hrm.domain.entities.shift import Shift
from src.modules.hrm.infrastructure.mappers.shift_mapper import ShiftMapper
from src.modules.hrm.infrastructure.models.shift_model import ShiftModel


class SqlAlchemyShiftRepository:
    """Truy xuất mẫu ca từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lay_model(self, shift_id: UUID) -> ShiftModel | None:
        ket_qua = await self._session.execute(select(ShiftModel).where(ShiftModel.id == shift_id))
        return ket_qua.scalar_one_or_none()

    async def get_by_id(self, shift_id: UUID) -> Shift | None:
        model = await self._lay_model(shift_id)
        return ShiftMapper.to_domain(model) if model else None

    async def add(self, shift: Shift) -> None:
        self._session.add(ShiftMapper.to_model(shift))

    async def update(self, shift: Shift) -> None:
        model = await self._lay_model(shift.id)
        if model is None:
            raise ValueError(f"Không tìm thấy mẫu ca {shift.id} để cập nhật.")
        ShiftMapper.update_model(model, shift)

    async def list_for_departments(
        self, department_ids: list[UUID] | None, is_active: bool | None = None
    ) -> list[Shift]:
        # Danh sách phòng rỗng nghĩa là không phòng nào — trả rỗng, không truy vấn.
        if department_ids is not None and not department_ids:
            return []

        cau = select(ShiftModel)
        if department_ids is not None:
            cau = cau.where(ShiftModel.department_id.in_(department_ids))
        if is_active is not None:
            cau = cau.where(ShiftModel.is_active == is_active)
        cau = cau.order_by(ShiftModel.created_at)
        ket_qua = await self._session.execute(cau)
        return [ShiftMapper.to_domain(m) for m in ket_qua.scalars()]
