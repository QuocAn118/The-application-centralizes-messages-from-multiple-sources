"""Interface repository cho ShiftAssignment (buổi phân ca)."""

from datetime import date
from typing import Protocol
from uuid import UUID

from src.modules.hrm.domain.entities.shift_assignment import ShiftAssignment


class IShiftAssignmentRepository(Protocol):
    """Truy xuất buổi phân ca."""

    async def get_by_id(self, assignment_id: UUID) -> ShiftAssignment | None: ...

    async def add(self, assignment: ShiftAssignment) -> None: ...

    async def update(self, assignment: ShiftAssignment) -> None: ...

    async def list_active_for_user_on_date(
        self, user_id: UUID, work_date: date
    ) -> list[ShiftAssignment]:
        """Các buổi phân ca còn hiệu lực của một nhân viên trong một ngày.

        Use case ``AssignShift`` dùng để kiểm chồng ca trước khi thêm buổi mới.
        """
        ...

    async def list_for_scope(
        self,
        user_ids: list[UUID] | None,
        department_ids: list[UUID] | None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ShiftAssignment]:
        """Liệt kê buổi phân ca theo phạm vi.

        ``user_ids`` lọc theo nhân viên (Staff xem của mình); ``department_ids``
        lọc theo phòng (Manager xem phòng mình). ``None`` ở cả hai nghĩa là
        không giới hạn (Admin). Khoảng ngày tuỳ chọn.
        """
        ...
