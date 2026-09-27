"""Lỗi thuộc tầng application."""

from typing import Any


class ApplicationError(Exception):
    """Lỗi gốc của tầng application.

    ``details`` (tuỳ chọn) đi thẳng ra ``error.details`` của phản hồi — chỉ đặt
    dữ liệu người gọi ĐƯỢC PHÉP thấy.
    """

    def __init__(self, message: str, code: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details


class NotFoundError(ApplicationError):
    """Không tìm thấy tài nguyên được yêu cầu."""


class ConflictError(ApplicationError):
    """Thao tác xung đột với trạng thái hiện tại của dữ liệu."""


class PermissionDeniedError(ApplicationError):
    """Người gọi đã xác thực nhưng không đủ quyền."""


class AuthenticationError(ApplicationError):
    """Người gọi chưa xác thực hoặc thông tin xác thực không hợp lệ."""
