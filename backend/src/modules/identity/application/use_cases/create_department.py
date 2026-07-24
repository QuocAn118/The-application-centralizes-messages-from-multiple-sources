"""Use case tạo phòng ban."""

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import ConflictError, PermissionDeniedError
from src.shared.application.ports import IClock


class DepartmentNameAlreadyExistsError(ConflictError):
    """Tên phòng ban đã tồn tại trong các phòng đang hoạt động."""

    def __init__(self, ten: str) -> None:
        super().__init__(
            f"Phòng ban {ten!r} đã tồn tại.", code="DEPARTMENT_NAME_EXISTS"
        )


class CreateDepartment:
    """Tạo phòng ban mới. Chỉ quản trị viên được phép."""

    def __init__(
        self,
        department_repo: IDepartmentRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._department_repo = department_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(
        self, requester: User, name: str, description: str | None = None
    ) -> Department:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được tạo phòng ban.", code="ADMIN_REQUIRED"
            )

        if await self._department_repo.get_by_name(name) is not None:
            raise DepartmentNameAlreadyExistsError(name.strip())

        bay_gio = self._clock.now()
        phong = Department.create(name=name, description=description, now=bay_gio)
        await self._department_repo.add(phong)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.DEPARTMENT_CREATED,
                actor_id=requester.id,
                resource_type="department",
                resource_id=str(phong.id),
                now=bay_gio,
                changes={"name": phong.name},
            )
        )
        return phong
