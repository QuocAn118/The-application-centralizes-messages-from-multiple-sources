"""Use case vô hiệu hoá phòng ban."""

from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class DeactivateDepartment:
    """Vô hiệu hoá phòng ban.

    Số nhân viên đang hoạt động được đếm ở đây rồi truyền vào entity — domain
    không truy cập repository.
    """

    def __init__(
        self,
        department_repo: IDepartmentRepository,
        user_repo: IUserRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._department_repo = department_repo
        self._user_repo = user_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(self, requester: User, department_id: UUID) -> Department:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được vô hiệu hoá phòng ban.",
                code="ADMIN_REQUIRED",
            )

        phong = await self._department_repo.get_by_id(department_id)
        if phong is None:
            raise NotFoundError(
                "Không tìm thấy phòng ban.", code="DEPARTMENT_NOT_FOUND"
            )

        so_nhan_vien = await self._user_repo.count_active_in_department(department_id)

        bay_gio = self._clock.now()
        phong.deactivate(active_member_count=so_nhan_vien, now=bay_gio)
        await self._department_repo.update(phong)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.DEPARTMENT_DEACTIVATED,
                actor_id=requester.id,
                resource_type="department",
                resource_id=str(phong.id),
                now=bay_gio,
            )
        )
        return phong
