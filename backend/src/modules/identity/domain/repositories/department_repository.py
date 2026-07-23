"""Interface repository cho phòng ban."""

from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.entities.department import Department


class IDepartmentRepository(Protocol):
    """Truy xuất và lưu trữ phòng ban."""

    async def get_by_id(self, department_id: UUID) -> Department | None: ...

    async def get_by_name(self, name: str) -> Department | None:
        """Tìm theo tên, không phân biệt hoa thường, chỉ trong phòng đang hoạt động."""
        ...

    async def add(self, department: Department) -> None: ...

    async def update(self, department: Department) -> None: ...

    async def list_departments(
        self,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Department]: ...

    async def count_departments(self, is_active: bool | None = None) -> int: ...
