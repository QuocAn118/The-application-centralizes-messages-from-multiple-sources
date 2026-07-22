"""Value object địa chỉ email."""

import re
from dataclasses import dataclass

from src.shared.domain.exceptions import DomainError

_DINH_DANG_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InvalidEmailError(DomainError):
    """Địa chỉ email không đúng định dạng."""

    def __init__(self, gia_tri: str) -> None:
        super().__init__(
            f"Địa chỉ email không hợp lệ: {gia_tri!r}",
            code="INVALID_EMAIL",
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
        object.__setattr__(self, "value", chuan_hoa)

    def __str__(self) -> str:
        return self.value
