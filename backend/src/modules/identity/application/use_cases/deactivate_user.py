"""Use case vô hiệu hoá người dùng."""

from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.refresh_token_repository import (
    IRefreshTokenRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class DeactivateUser:
    """Vô hiệu hoá tài khoản và thu hồi mọi phiên đăng nhập.

    Access token đang lưu hành vẫn dùng được tới khi hết hạn — giới hạn đã
    biết, xem mục 9 của spec.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        refresh_token_repo: IRefreshTokenRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(self, requester: User, user_id: UUID) -> User:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được vô hiệu hoá tài khoản.",
                code="ADMIN_REQUIRED",
            )

        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy người dùng.", code="USER_NOT_FOUND")

        so_admin = await self._user_repo.count_active_admins()
        la_admin_cuoi = user.role is Role.ADMIN and user.is_active and so_admin <= 1

        bay_gio = self._clock.now()
        user.deactivate(is_last_active_admin=la_admin_cuoi, now=bay_gio)
        await self._user_repo.update(user)
        await self._refresh_token_repo.revoke_all_for_user(user.id, now=bay_gio)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_DEACTIVATED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
            )
        )
        return user
