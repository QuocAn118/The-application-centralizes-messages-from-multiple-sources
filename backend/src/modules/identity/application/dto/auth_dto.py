"""DTO cho luồng xác thực."""

from dataclasses import dataclass

from src.modules.identity.domain.entities.user import User


@dataclass(frozen=True)
class TokenPair:
    """Cặp token trả về sau khi đăng nhập hoặc làm mới."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


@dataclass(frozen=True)
class LoginResult:
    """Kết quả đăng nhập.

    ``must_change_password`` được nâng lên đây để client biết cần chuyển hướng
    sang màn hình đổi mật khẩu mà không phải đọc sâu vào ``user``.
    """

    tokens: TokenPair
    user: User
    must_change_password: bool
