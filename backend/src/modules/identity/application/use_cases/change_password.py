"""Use case đổi mật khẩu."""

from src.modules.identity.application.ports import IPasswordHasher
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
from src.shared.application.exceptions import ApplicationError
from src.shared.application.ports import IClock

DO_DAI_MAT_KHAU_TOI_THIEU = 8


class WeakPasswordError(ApplicationError):
    """Mật khẩu mới không đạt yêu cầu tối thiểu."""

    def __init__(self, ly_do: str) -> None:
        super().__init__(ly_do, code="WEAK_PASSWORD")


class InvalidCurrentPasswordError(ApplicationError):
    """Mật khẩu hiện tại không đúng."""

    def __init__(self) -> None:
        super().__init__(
            "Mật khẩu hiện tại không đúng.", code="INVALID_CURRENT_PASSWORD"
        )


def kiem_tra_do_manh(mat_khau: str) -> None:
    """Kiểm tra yêu cầu tối thiểu cho mật khẩu.

    Chỉ đặt ngưỡng độ dài và yêu cầu có cả chữ lẫn số. Không ép ký tự đặc biệt
    — quy tắc càng rườm rà, người dùng càng có xu hướng ghi mật khẩu ra giấy.
    """
    if len(mat_khau) < DO_DAI_MAT_KHAU_TOI_THIEU:
        raise WeakPasswordError(
            f"Mật khẩu phải có ít nhất {DO_DAI_MAT_KHAU_TOI_THIEU} ký tự."
        )
    if not any(k.isalpha() for k in mat_khau):
        raise WeakPasswordError("Mật khẩu phải chứa ít nhất một chữ cái.")
    if not any(k.isdigit() for k in mat_khau):
        raise WeakPasswordError("Mật khẩu phải chứa ít nhất một chữ số.")


class ChangePassword:
    """Người dùng tự đổi mật khẩu của mình."""

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
        self, requester: User, current_password: str, new_password: str
    ) -> None:
        if not self._hasher.verify(
            current_password, requester.password_hash.value
        ):
            raise InvalidCurrentPasswordError

        kiem_tra_do_manh(new_password)

        bay_gio = self._clock.now()
        requester.set_password(
            PasswordHash(self._hasher.hash(new_password)),
            must_change=False,
            now=bay_gio,
        )
        await self._user_repo.update(requester)

        # Đổi mật khẩu phải đá mọi phiên khác ra: nếu mật khẩu cũ đã bị lộ,
        # kẻ tấn công không được tiếp tục dùng refresh token của họ.
        await self._refresh_token_repo.revoke_all_for_user(
            requester.id, now=bay_gio
        )

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_PASSWORD_CHANGED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(requester.id),
                now=bay_gio,
            )
        )
