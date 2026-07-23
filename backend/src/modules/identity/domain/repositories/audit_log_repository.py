"""Interface repository cho nhật ký kiểm toán."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog


class IAuditLogRepository(Protocol):
    """Ghi và tra cứu nhật ký kiểm toán."""

    async def add(self, entry: AuditLog) -> None: ...

    async def list_entries(
        self,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Danh sách bản ghi, mới nhất trước."""
        ...

    async def count_entries(
        self,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> int: ...
