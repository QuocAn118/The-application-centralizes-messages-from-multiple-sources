"""Use case đăng nhập."""

from datetime import timedelta

from src.modules.identity.application.dto.auth_dto import LoginResult, TokenPair
from src.modules.identity.application.ports import IPasswordHasher, ITokenService
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.refresh_token_repository import (
    IRefreshTokenRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.email import Email, InvalidEmailError
from src.shared.application.exceptions import ApplicationError
from src.shared.application.ports import IClock


class InvalidCredentialsError(ApplicationError):
    """Email hoặc mật khẩu không đúng.

    Cố ý không phân biệt hai trường hợp: nói rõ email nào có tồn tại là giúp
    kẻ tấn công dò danh sách tài khoản.
    """

    def __init__(self) -> None:
        super().__init__("Email hoặc mật khẩu không đúng.", code="INVALID_CREDENTIALS")


class InactiveAccountError(ApplicationError):
    """Tài khoản đã bị vô hiệu hoá."""

    def __init__(self) -> None:
        super().__init__(
            "Tài khoản đã bị vô hiệu hoá. Vui lòng liên hệ quản trị viên.",
            code="INACTIVE_ACCOUNT",
        )


class LoginUser:
    """Xác thực người dùng và cấp cặp token."""

    def __init__(
        self,
        user_repo: IUserRepository,
        refresh_token_repo: IRefreshTokenRepository,
        audit_repo: IAuditLogRepository,
        hasher: IPasswordHasher,
        token_service: ITokenService,
        clock: IClock,
        refresh_token_expire_days: int,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._audit_repo = audit_repo
        self._hasher = hasher
        self._token_service = token_service
        self._clock = clock
        self._refresh_token_expire = timedelta(days=refresh_token_expire_days)

    async def _ghi_that_bai(
        self, email: str, ip_address: str | None, user_agent: str | None
    ) -> None:
        """Ghi nhật ký đăng nhập thất bại.

        Chỉ lưu email được thử, tuyệt đối không lưu mật khẩu.
        """
        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.AUTH_LOGIN_FAILED,
                actor_id=None,
                resource_type="auth",
                resource_id=None,
                now=self._clock.now(),
                changes={"email_da_thu": email},
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )

    async def execute(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginResult:
        try:
            dia_chi = Email(email)
        except InvalidEmailError as loi:
            await self._ghi_that_bai(email, ip_address, user_agent)
            raise InvalidCredentialsError from loi

        user = await self._user_repo.get_by_email(dia_chi)

        if user is None or not self._hasher.verify(password, user.password_hash.value):
            await self._ghi_that_bai(email, ip_address, user_agent)
            raise InvalidCredentialsError

        if not user.is_active:
            await self._ghi_that_bai(email, ip_address, user_agent)
            raise InactiveAccountError

        bay_gio = self._clock.now()
        user.record_login(now=bay_gio)
        await self._user_repo.update(user)

        access_token = self._token_service.create_access_token(
            user_id=user.id, role=user.role, department_id=user.department_id
        )
        tho, chuoi_hash = self._token_service.create_refresh_token()
        await self._refresh_token_repo.add(
            RefreshToken.issue(
                user_id=user.id,
                token_hash=chuoi_hash,
                expires_at=bay_gio + self._refresh_token_expire,
                now=bay_gio,
                user_agent=user_agent,
                ip_address=ip_address,
            )
        )

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.AUTH_LOGIN_SUCCEEDED,
                actor_id=user.id,
                resource_type="auth",
                resource_id=str(user.id),
                now=bay_gio,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )

        payload = self._token_service.decode_access_token(access_token)

        return LoginResult(
            tokens=TokenPair(
                access_token=access_token,
                refresh_token=tho,
                expires_in=payload.lifetime_seconds,
            ),
            user=user,
            must_change_password=user.must_change_password,
        )
