"""Use case chuyển người dùng sang phòng ban khác."""

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


class AssignUserToDepartment:
    """Chuyển người dùng sang phòng ban khác, giữ nguyên vai trò."""

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

    async def execute(
        self, requester: User, user_id: UUID, department_id: UUID | None
    ) -> User:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được chuyển phòng ban.", code="ADMIN_REQUIRED"
            )

        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy người dùng.", code="USER_NOT_FOUND")

        if department_id is not None:
            phong = await self._department_repo.get_by_id(department_id)
            if phong is None or not phong.is_active:
                raise NotFoundError(
                    "Không tìm thấy phòng ban đang hoạt động.",
                    code="DEPARTMENT_NOT_FOUND",
                )

        da_co_quan_ly = False
        if department_id is not None:
            da_co_quan_ly = await self._user_repo.has_active_manager(
                department_id, exclude_user_id=user.id
            )

        phong_cu = user.department_id
        bay_gio = self._clock.now()
        user.assign_to_department(
            department_id=department_id,
            department_has_active_manager=da_co_quan_ly,
            now=bay_gio,
        )
        await self._user_repo.update(user)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_DEPARTMENT_CHANGED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
                changes={
                    "department_id": {
                        "truoc": str(phong_cu) if phong_cu else None,
                        "sau": str(department_id) if department_id else None,
                    }
                },
            )
        )
        return user
