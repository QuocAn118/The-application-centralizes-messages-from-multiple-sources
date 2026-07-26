"""Interface repository cho Shift (mẫu ca)."""

from typing import Protocol
from uuid import UUID

from src.modules.hrm.domain.entities.shift import Shift


class IShiftRepository(Protocol):
    """Truy xuất mẫu ca."""

    async def get_by_id(self, shift_id: UUID) -> Shift | None: ...

    async def add(self, shift: Shift) -> None: ...

    async def update(self, shift: Shift) -> None: ...

    async def list_for_departments(
        self, department_ids: list[UUID] | None, is_active: bool | None = None
    ) -> list[Shift]:
        """Liệt kê mẫu ca theo phạm vi phòng ban.

        ``department_ids=None`` nghĩa là không giới hạn phòng (Admin). Danh sách
        rỗng nghĩa là không phòng nào — không trả gì.
        """
        ...
