"""Interface repository cho LeaveRequest (đơn từ)."""

from typing import Protocol
from uuid import UUID

from src.modules.hrm.domain.entities.leave_request import LeaveRequest
from src.modules.hrm.domain.value_objects.request_kind import RequestStatus


class IRequestRepository(Protocol):
    """Truy xuất đơn từ."""

    async def get_by_id(self, request_id: UUID) -> LeaveRequest | None: ...

    async def add(self, request: LeaveRequest) -> None: ...

    async def update(self, request: LeaveRequest) -> None: ...

    async def list_for_scope(
        self,
        requester_id: UUID | None,
        department_ids: list[UUID] | None,
        status: RequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LeaveRequest]:
        """Liệt kê đơn theo phạm vi.

        ``requester_id`` lọc đơn của một người (Staff xem của mình);
        ``department_ids`` lọc theo phòng (Manager xem phòng mình). Truyền cả
        hai để lấy hợp của 'đơn mình gửi' và 'đơn trong phòng mình' (Manager
        vừa gửi đơn vừa duyệt đơn). ``None`` cả hai nghĩa là không giới hạn
        (Admin).
        """
        ...

    async def count_for_scope(
        self,
        requester_id: UUID | None,
        department_ids: list[UUID] | None,
        status: RequestStatus | None = None,
    ) -> int: ...
