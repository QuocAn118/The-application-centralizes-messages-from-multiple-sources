"""Cầu nối keyword → identity: chỗ DUY NHẤT trong keyword được biết identity tồn tại.

Implementation của port ``IWorkforceDirectory``. Nhờ ranh giới này, toàn bộ
domain/application/presentation của keyword không import identity (import-linter
xác nhận); chỉ file infrastructure này đọc dữ liệu identity. Dùng để *gác* kết
quả LLM: phòng LLM chọn phải thật sự tồn tại và đang hoạt động mới được tự phân.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)


class IdentityWorkforceDirectory:
    """Kiểm phòng tồn tại/đang hoạt động qua identity, cho use case keyword."""

    def __init__(self, session: AsyncSession) -> None:
        self._department_repo = SqlAlchemyDepartmentRepository(session)

    async def department_exists_active(self, department_id: UUID) -> bool:
        department = await self._department_repo.get_by_id(department_id)
        return department is not None and department.is_active
