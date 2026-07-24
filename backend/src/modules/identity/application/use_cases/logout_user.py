"""Use case đăng xuất."""

from src.modules.identity.application.ports import ITokenService
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.refresh_token_repository import (
    IRefreshTokenRepository,
)
from src.shared.application.ports import IClock


class LogoutUser:
    """Thu hồi refresh token của phiên hiện tại.

    Access token vẫn còn hiệu lực tới khi hết hạn — xem mục 9 của spec về giới
    hạn này.
    """

    def __init__(
        self,
        refresh_token_repo: IRefreshTokenRepository,
        audit_repo: IAuditLogRepository,
        token_service: ITokenService,
        clock: IClock,
    ) -> None:
        self._refresh_token_repo = refresh_token_repo
        self._audit_repo = audit_repo
        self._token_service = token_service
        self._clock = clock

    async def execute(self, refresh_token: str, requester: User) -> None:
        """Đăng xuất.

        Không báo lỗi khi token không tồn tại: đăng xuất hai lần, hoặc đăng
        xuất bằng token đã hết hạn, đều nên coi là thành công.
        """
        bay_gio = self._clock.now()
        chuoi_hash = self._token_service.hash_refresh_token(refresh_token)
        token = await self._refresh_token_repo.get_by_hash(chuoi_hash)

        if token is not None and token.user_id == requester.id:
            token.revoke(now=bay_gio)
            await self._refresh_token_repo.update(token)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.AUTH_LOGOUT,
                actor_id=requester.id,
                resource_type="auth",
                resource_id=str(requester.id),
                now=bay_gio,
            )
        )
