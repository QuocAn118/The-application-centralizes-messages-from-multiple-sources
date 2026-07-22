"""Value object địa chỉ email."""

import re
from dataclasses import dataclass

from src.shared.domain.exceptions import DomainError

_DINH_DANG_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Giới hạn của RFC 5321 và cũng là độ rộng cột ``users.email`` (VARCHAR 320).
# Domain phải từ chối thứ mà cơ sở dữ liệu không lưu nổi, nếu không lỗi sẽ nổ ở
# tầng lưu trữ dưới dạng DataError khó truy nguyên.
DO_DAI_EMAIL_TOI_DA = 320


class InvalidEmailError(DomainError):
    """Địa chỉ email không đúng định dạng."""

    def __init__(self, gia_tri: str) -> None:
        super().__init__(
            f"Địa chỉ email không hợp lệ: {gia_tri!r}",
            code="INVALID_EMAIL",
        )


class EmailTooLongError(DomainError):
    """Địa chỉ email vượt quá độ dài tối đa."""

    def __init__(self, do_dai: int) -> None:
        super().__init__(
            f"Địa chỉ email dài {do_dai} ký tự, vượt quá giới hạn "
            f"{DO_DAI_EMAIL_TOI_DA} ký tự.",
            code="EMAIL_TOO_LONG",
        )


@dataclass(frozen=True)
class Email:
    """Địa chỉ email đã được chuẩn hoá.

    Chuẩn hoá về chữ thường ngay khi khởi tạo, nên hai địa chỉ chỉ khác nhau
    ở kiểu chữ sẽ bằng nhau. Nhờ đó ràng buộc duy nhất ở cơ sở dữ liệu
    (index trên ``lower(email)``) khớp với hành vi của tầng domain.
    """

    value: str

    def __post_init__(self) -> None:
        chuan_hoa = self.value.strip().lower()
        if not _DINH_DANG_EMAIL.match(chuan_hoa):
            raise InvalidEmailError(self.value)
        if len(chuan_hoa) > DO_DAI_EMAIL_TOI_DA:
            raise EmailTooLongError(len(chuan_hoa))
        object.__setattr__(self, "value", chuan_hoa)

    def __str__(self) -> str:
        return self.value
