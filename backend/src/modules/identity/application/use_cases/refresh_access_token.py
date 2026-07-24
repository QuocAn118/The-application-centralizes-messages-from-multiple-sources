"""Use case làm mới access token."""

from datetime import timedelta

from src.modules.identity.application.dto.auth_dto import TokenPair
from src.modules.identity.application.ports import ITokenService
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.refresh_token_repository import (
    IRefreshTokenRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.shared.application.exceptions import AuthenticationError
from src.shared.application.ports import IClock, ITransaction


class InvalidRefreshTokenError(AuthenticationError):
    """Refresh token không tồn tại, đã hết hạn, hoặc đã bị thu hồi."""

    def __init__(self) -> None:
        super().__init__(
            "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.",
            code="INVALID_REFRESH_TOKEN",
        )


class RefreshAccessToken:
    """Đổi refresh token lấy cặp token mới.

    Mỗi lần làm mới sinh refresh token mới và thu hồi token cũ (rotation). Nếu
    một token đã bị thay thế lại được gửi lên, đó là dấu hiệu token bị đánh cắp
    — khi đó toàn bộ chuỗi token bị thu hồi, buộc cả kẻ tấn công lẫn người dùng
    thật phải đăng nhập lại.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        refresh_token_repo: IRefreshTokenRepository,
        audit_repo: IAuditLogRepository,
        token_service: ITokenService,
        clock: IClock,
        transaction: ITransaction,
        refresh_token_expire_days: int,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._audit_repo = audit_repo
        self._token_service = token_service
        self._clock = clock
        self._transaction = transaction
        self._refresh_token_expire = timedelta(days=refresh_token_expire_days)

    async def execute(
        self,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPair:
        bay_gio = self._clock.now()
        chuoi_hash = self._token_service.hash_refresh_token(refresh_token)
        token_cu = await self._refresh_token_repo.get_by_hash(chuoi_hash)

        if token_cu is None:
            raise InvalidRefreshTokenError

        if token_cu.replaced_by_id is not None:
            # Token này đã được xoay trước đó mà vẫn có người dùng lại — dấu
            # hiệu bị đánh cắp. Thu hồi cả chuỗi.
            await self._refresh_token_repo.revoke_chain(token_cu, now=bay_gio)
            await self._audit_repo.add(
                AuditLog.record(
                    action=AuditAction.AUTH_TOKEN_REUSE_DETECTED,
                    actor_id=token_cu.user_id,
                    resource_type="auth",
                    resource_id=str(token_cu.user_id),
                    now=bay_gio,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
            # Chốt giao dịch trước khi ném lỗi: nếu không, lớp HTTP sẽ rollback
            # theo lỗi và xoá luôn việc thu hồi chuỗi, khiến kẻ tấn công vẫn
            # dùng được token đã lộ.
            await self._transaction.commit()
            raise InvalidRefreshTokenError

        if not token_cu.is_valid(now=bay_gio):
            raise InvalidRefreshTokenError

        user = await self._user_repo.get_by_id(token_cu.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError

        tho_moi, hash_moi = self._token_service.create_refresh_token()
        token_moi = RefreshToken.issue(
            user_id=user.id,
            token_hash=hash_moi,
            expires_at=bay_gio + self._refresh_token_expire,
            now=bay_gio,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self._refresh_token_repo.add(token_moi)

        token_cu.rotate_to(new_token_id=token_moi.id, now=bay_gio)
        await self._refresh_token_repo.update(token_cu)

        access_token = self._token_service.create_access_token(
            user_id=user.id, role=user.role, department_id=user.department_id
        )
        payload = self._token_service.decode_access_token(access_token)

        return TokenPair(
            access_token=access_token,
            refresh_token=tho_moi,
            expires_in=payload.lifetime_seconds,
        )
