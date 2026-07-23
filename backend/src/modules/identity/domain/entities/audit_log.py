"""Entity bản ghi nhật ký kiểm toán."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from src.shared.domain.entity import Entity


class AuditAction(StrEnum):
    """Các hành động được ghi nhật ký.

    Giá trị dùng dạng ``<đối tượng>.<hành động>`` để lọc theo tiền tố khi
    tra cứu, ví dụ mọi hành động xác thực đều bắt đầu bằng ``auth.``.
    """

    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DEACTIVATED = "user.deactivated"
    USER_REACTIVATED = "user.reactivated"
    USER_ROLE_CHANGED = "user.role_changed"
    USER_DEPARTMENT_CHANGED = "user.department_changed"
    USER_PASSWORD_RESET = "user.password_reset"
    USER_PASSWORD_CHANGED = "user.password_changed"

    DEPARTMENT_CREATED = "department.created"
    DEPARTMENT_UPDATED = "department.updated"
    DEPARTMENT_DEACTIVATED = "department.deactivated"

    AUTH_LOGIN_SUCCEEDED = "auth.login_succeeded"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_REUSE_DETECTED = "auth.token_reuse_detected"


@dataclass(eq=False, kw_only=True)
class AuditLog(Entity):
    """Bản ghi một hành động đã xảy ra trong hệ thống.

    Chỉ ghi thêm: entity này cố ý không có phương thức sửa hay xoá.
    """

    action: AuditAction
    resource_type: str
    created_at: datetime
    actor_id: UUID | None = None
    resource_id: str | None = None
    changes: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    @classmethod
    def record(
        cls,
        action: AuditAction,
        actor_id: UUID | None,
        resource_type: str,
        resource_id: str | None,
        now: datetime,
        changes: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> "AuditLog":
        """Tạo bản ghi nhật ký.

        ``actor_id`` là ``None`` khi hành động do hệ thống thực hiện hoặc khi
        chưa xác định được người gọi, ví dụ đăng nhập thất bại.
        """
        return cls(
            action=action,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
        )
