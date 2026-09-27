"""Port lưu ghi chú nội bộ về khách (BE-5)."""

from typing import Protocol
from uuid import UUID

from src.modules.inbox.domain.entities.customer_note import CustomerNote


class ICustomerNoteRepository(Protocol):
    async def add(self, note: CustomerNote) -> None: ...

    async def get_by_id(self, note_id: UUID) -> CustomerNote | None: ...

    async def list_for_customer(
        self, customer_id: UUID, *, tat_ca_phong: bool, department_id: UUID | None
    ) -> list[CustomerNote]:
        """Mới trước. ``tat_ca_phong`` (Admin) bỏ lọc; ngược lại chỉ đúng ``department_id``
        (``None`` so khớp ``IS NULL`` — không phải "mọi phòng")."""
        ...

    async def delete(self, note_id: UUID) -> None: ...
