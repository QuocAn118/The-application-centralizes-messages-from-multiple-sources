"""Repository phòng ban dùng SQLAlchemy."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.infrastructure.mappers.department_mapper import (
    DepartmentMapper,
)
from src.modules.identity.infrastructure.models.department_model import DepartmentModel


class SqlAlchemyDepartmentRepository:
    """Truy xuất phòng ban từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lay_model(self, department_id: UUID) -> DepartmentModel | None:
        ket_qua = await self._session.execute(
            select(DepartmentModel).where(DepartmentModel.id == department_id)
        )
        return ket_qua.scalar_one_or_none()

    async def get_by_id(self, department_id: UUID) -> Department | None:
        model = await self._lay_model(department_id)
        return DepartmentMapper.to_domain(model) if model else None

    async def get_by_name(self, name: str) -> Department | None:
        """Tìm trong các phòng ban đang hoạt động, không phân biệt hoa thường."""
        ket_qua = await self._session.execute(
            select(DepartmentModel).where(
                func.lower(DepartmentModel.name) == name.strip().lower(),
                DepartmentModel.is_active,
            )
        )
        model = ket_qua.scalar_one_or_none()
        return DepartmentMapper.to_domain(model) if model else None

    async def add(self, department: Department) -> None:
        self._session.add(DepartmentMapper.to_model(department))

    async def update(self, department: Department) -> None:
        model = await self._lay_model(department.id)
        if model is None:
            raise ValueError(f"Không tìm thấy phòng ban {department.id} để cập nhật.")
        DepartmentMapper.update_model(model, department)

    async def list_departments(
        self,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Department]:
        cau_truy_van = select(DepartmentModel)
        if is_active is not None:
            cau_truy_van = cau_truy_van.where(DepartmentModel.is_active == is_active)
        cau_truy_van = cau_truy_van.order_by(DepartmentModel.name).limit(limit).offset(offset)
        ket_qua = await self._session.execute(cau_truy_van)
        return [DepartmentMapper.to_domain(m) for m in ket_qua.scalars()]

    async def count_departments(self, is_active: bool | None = None) -> int:
        cau_truy_van = select(func.count()).select_from(DepartmentModel)
        if is_active is not None:
            cau_truy_van = cau_truy_van.where(DepartmentModel.is_active == is_active)
        ket_qua = await self._session.execute(cau_truy_van)
        return int(ket_qua.scalar_one())
