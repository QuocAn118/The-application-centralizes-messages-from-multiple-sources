"""Port bảo mật mà tầng application cần."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import ApplicationError


class InvalidTokenError(ApplicationError):
    """Token sai định dạng, sai chữ ký, hoặc thiếu trường bắt buộc."""

    def __init__(self) -> None:
        super().__init__("Token không hợp lệ.", code="INVALID_TOKEN")


class ExpiredTokenError(ApplicationError):
    """Token đã quá hạn sử dụng."""

    def __init__(self) -> None:
        super().__init__("Token đã hết hạn.", code="EXPIRED_TOKEN")


@dataclass(frozen=True)
class AccessTokenPayload:
    """Thông tin lấy được từ một access token hợp lệ."""

    user_id: UUID
    role: Role
    department_id: UUID | None
    issued_at: datetime
    expires_at: datetime

    @property
    def lifetime_seconds(self) -> int:
        """Tuổi thọ token tính bằng giây, đúng bằng ``exp - iat``.

        Lấy hiệu của hai mốc nằm trong chính token (đều là số giây nguyên) nên
        không bị lệch vì đọc lại đồng hồ ở thời điểm khác — đó là lý do
        ``expires_in`` phải tính từ đây chứ không phải ``exp - now``.
        """
        return int((self.expires_at - self.issued_at).total_seconds())


class IPasswordHasher(Protocol):
    """Băm và kiểm tra mật khẩu."""

    def hash(self, plain_password: str) -> str: ...

    def verify(self, plain_password: str, hashed: str) -> bool:
        """Trả về ``False`` khi sai mật khẩu hoặc khi chuỗi hash hỏng.

        Không được ném ngoại lệ: chuỗi hash hỏng trong cơ sở dữ liệu phải dẫn
        tới đăng nhập thất bại, không phải lỗi 500.
        """
        ...


class ITokenService(Protocol):
    """Cấp phát và kiểm tra token."""

    def create_access_token(self, user_id: UUID, role: Role, department_id: UUID | None) -> str: ...

    def decode_access_token(self, token: str) -> AccessTokenPayload:
        """Giải mã và kiểm tra token.

        Ném ``ExpiredTokenError`` nếu hết hạn, ``InvalidTokenError`` nếu chữ ký
        sai hoặc nội dung không đúng cấu trúc.
        """
        ...

    def create_refresh_token(self) -> tuple[str, str]:
        """Sinh refresh token mới.

        Trả về ``(token_thô, hash)``. Token thô gửi cho client, hash lưu vào
        cơ sở dữ liệu.
        """
        ...

    def hash_refresh_token(self, token: str) -> str:
        """Băm token thô để đối chiếu với giá trị đã lưu."""
        ...
