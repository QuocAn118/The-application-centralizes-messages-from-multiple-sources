"""Use case quản trị viên đặt lại mật khẩu cho người dùng."""

from uuid import UUID

from src.modules.identity.application.ports import IPasswordHasher
from src.modules.identity.application.use_cases.change_password import kiem_tra_do_manh
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.refresh_token_repository import (
    IRefreshTokenRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class ResetUserPassword:
    """Quản trị viên cấp mật khẩu tạm cho người dùng.

    Đây là cơ chế khôi phục duy nhất của hệ thống — không có chức năng quên
    mật khẩu qua email.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        refresh_token_repo: IRefreshTokenRepository,
        audit_repo: IAuditLogRepository,
        hasher: IPasswordHasher,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._audit_repo = audit_repo
        self._hasher = hasher
        self._clock = clock

    async def execute(
        self, requester: User, user_id: UUID, new_password: str
    ) -> None:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được đặt lại mật khẩu.", code="ADMIN_REQUIRED"
            )

        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy người dùng.", code="USER_NOT_FOUND")

        kiem_tra_do_manh(new_password)

        bay_gio = self._clock.now()
        user.set_password(
            PasswordHash(self._hasher.hash(new_password)),
            must_change=True,
            now=bay_gio,
        )
        await self._user_repo.update(user)
        await self._refresh_token_repo.revoke_all_for_user(user.id, now=bay_gio)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_PASSWORD_RESET,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
            )
        )
