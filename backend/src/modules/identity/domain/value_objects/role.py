"""Vai trò người dùng trong hệ thống."""

from enum import StrEnum


class Role(StrEnum):
    """Ba vai trò của OmniChat.

    Kế thừa ``StrEnum`` để so sánh trực tiếp với chuỗi, thuận tiện khi đọc
    giá trị từ cơ sở dữ liệu và khi ghi ra JSON.
    """

    STAFF = "STAFF"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"

    def requires_department(self) -> bool:
        """Vai trò này có bắt buộc thuộc một phòng ban không.

        Admin quản trị toàn hệ thống nên không gắn với phòng ban nào; Staff và
        Manager luôn thuộc đúng một phòng ban.
        """
        return self is not Role.ADMIN
