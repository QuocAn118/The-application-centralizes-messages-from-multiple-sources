"""Lỗi thuộc tầng domain."""


class DomainError(Exception):
    """Lỗi gốc của mọi vi phạm quy tắc nghiệp vụ.

    ``code`` là mã ổn định dùng cho API và cho frontend đối chiếu; ``message``
    là thông điệp tiếng Việt hiển thị cho người dùng.
    """

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class BusinessRuleViolationError(DomainError):
    """Một quy tắc nghiệp vụ bị vi phạm."""
