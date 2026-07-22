"""Value object chuỗi mật khẩu đã băm."""

from dataclasses import dataclass

from src.shared.domain.exceptions import DomainError


class InvalidPasswordHashError(DomainError):
    """Chuỗi hash mật khẩu rỗng hoặc không hợp lệ."""

    def __init__(self) -> None:
        super().__init__(
            "Chuỗi hash mật khẩu không được rỗng.",
            code="INVALID_PASSWORD_HASH",
        )


@dataclass(frozen=True)
class PasswordHash:
    """Bọc chuỗi mật khẩu đã băm.

    Tồn tại để kiểu dữ liệu tự nói lên rằng đây là hash chứ không phải mật khẩu
    thô, tránh nhầm lẫn khi truyền tham số. ``__repr__`` được ghi đè để hash
    không lọt vào log hay thông báo lỗi.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise InvalidPasswordHashError

    def __repr__(self) -> str:
        return "PasswordHash(<đã ẩn>)"

    def __str__(self) -> str:
        return "<đã ẩn>"
