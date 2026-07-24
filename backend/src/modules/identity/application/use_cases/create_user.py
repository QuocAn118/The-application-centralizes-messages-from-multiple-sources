"""Use case tạo người dùng."""

from uuid import UUID

from src.modules.identity.application.ports import IPasswordHasher
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import (
    DepartmentAlreadyHasManagerError,
    User,
)
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.shared.application.ports import IClock


class EmailAlreadyExistsError(ConflictError):
    """Email đã được dùng cho một tài khoản khác."""

    def __init__(self, email: str) -> None:
        super().__init__(
            f"Email {email} đã được sử dụng.", code="EMAIL_ALREADY_EXISTS"
        )


class CreateUser:
    """Tạo tài khoản mới. Chỉ quản trị viên được phép."""

    def __init__(
        self,
        user_repo: IUserRepository,
        department_repo: IDepartmentRepository,
        audit_repo: IAuditLogRepository,
        hasher: IPasswordHasher,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._department_repo = department_repo
        self._audit_repo = audit_repo
        self._hasher = hasher
        self._clock = clock

    async def execute(
        self,
        requester: User,
        email: str,
        full_name: str,
        role: Role,
        department_id: UUID | None,
        password: str,
        phone: str | None = None,
    ) -> User:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được tạo tài khoản.", code="ADMIN_REQUIRED"
            )

        dia_chi = Email(email)
        if await self._user_repo.get_by_email(dia_chi) is not None:
            raise EmailAlreadyExistsError(dia_chi.value)

        if department_id is not None:
            phong = await self._department_repo.get_by_id(department_id)
            if phong is None or not phong.is_active:
                raise NotFoundError(
                    "Không tìm thấy phòng ban đang hoạt động.",
                    code="DEPARTMENT_NOT_FOUND",
                )

        if (
            role is Role.MANAGER
            and department_id is not None
            and await self._user_repo.has_active_manager(department_id)
        ):
            raise DepartmentAlreadyHasManagerError

        bay_gio = self._clock.now()
        user = User.create(
            email=dia_chi,
            password_hash=PasswordHash(self._hasher.hash(password)),
            full_name=full_name,
            role=role,
            department_id=department_id,
            now=bay_gio,
            phone=phone,
            must_change_password=True,
        )
        await self._user_repo.add(user)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_CREATED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
                changes={
                    "email": user.email.value,
                    "role": user.role.value,
                    "department_id": str(department_id) if department_id else None,
                },
            )
        )
        return user
