"""Use case cập nhật phòng ban."""

from uuid import UUID

from src.modules.identity.application.use_cases.create_department import (
    DepartmentNameAlreadyExistsError,
)
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
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class UpdateDepartment:
    """Sửa tên và mô tả phòng ban."""

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
        self,
        requester: User,
        department_id: UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> Department:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được sửa phòng ban.", code="ADMIN_REQUIRED"
            )

        phong = await self._department_repo.get_by_id(department_id)
        if phong is None:
            raise NotFoundError(
                "Không tìm thấy phòng ban.", code="DEPARTMENT_NOT_FOUND"
            )

        bay_gio = self._clock.now()
        ten_cu = phong.name

        if name is not None:
            trung = await self._department_repo.get_by_name(name)
            # Đổi tên thành chính tên cũ không phải là trùng lặp.
            if trung is not None and trung.id != phong.id:
                raise DepartmentNameAlreadyExistsError(name.strip())
            phong.rename(name, now=bay_gio)

        if description is not None:
            phong.update_description(description, now=bay_gio)

        await self._department_repo.update(phong)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.DEPARTMENT_UPDATED,
                actor_id=requester.id,
                resource_type="department",
                resource_id=str(phong.id),
                now=bay_gio,
                changes={"name": {"truoc": ten_cu, "sau": phong.name}},
            )
        )
        return phong
