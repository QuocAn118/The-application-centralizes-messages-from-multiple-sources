"""Use case kích hoạt lại người dùng."""

from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
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


class ReactivateUser:
    """Kích hoạt lại tài khoản đã bị vô hiệu hoá."""

    def __init__(
        self,
        user_repo: IUserRepository,
        department_repo: IDepartmentRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._department_repo = department_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(self, requester: User, user_id: UUID) -> User:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được kích hoạt lại tài khoản.",
                code="ADMIN_REQUIRED",
            )

        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy người dùng.", code="USER_NOT_FOUND")

        phong_dang_hoat_dong = True
        phong_da_co_quan_ly = False
        if user.department_id is not None:
            phong = await self._department_repo.get_by_id(user.department_id)
            phong_dang_hoat_dong = phong is not None and phong.is_active
            phong_da_co_quan_ly = await self._user_repo.has_active_manager(
                user.department_id, exclude_user_id=user.id
            )

        bay_gio = self._clock.now()
        user.reactivate(
            department_is_active=phong_dang_hoat_dong,
            department_has_active_manager=phong_da_co_quan_ly,
            now=bay_gio,
        )
        await self._user_repo.update(user)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_REACTIVATED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
            )
        )
        return user
