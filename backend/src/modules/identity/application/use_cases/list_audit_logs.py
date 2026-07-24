"""Use case tra cứu nhật ký kiểm toán."""

from datetime import datetime
from uuid import UUID

from src.modules.identity.application.dto.user_dto import Page
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import PermissionDeniedError

GIOI_HAN_TOI_DA = 100


class ListAuditLogs:
    """Tra cứu nhật ký. Chỉ quản trị viên được phép.

    Nhật ký cho thấy toàn bộ hoạt động quản trị của hệ thống nên không mở cho
    quản lý cấp phòng.
    """

    def __init__(self, audit_repo: IAuditLogRepository) -> None:
        self._audit_repo = audit_repo

    async def execute(
        self,
        requester: User,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[AuditLog]:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được xem nhật ký hệ thống.",
                code="ADMIN_REQUIRED",
            )

        gioi_han = min(max(limit, 1), GIOI_HAN_TOI_DA)
        vi_tri = max(offset, 0)

        items = await self._audit_repo.list_entries(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            from_time=from_time,
            to_time=to_time,
            limit=gioi_han,
            offset=vi_tri,
        )
        tong = await self._audit_repo.count_entries(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            from_time=from_time,
            to_time=to_time,
        )
        return Page(items=items, total=tong, limit=gioi_han, offset=vi_tri)
