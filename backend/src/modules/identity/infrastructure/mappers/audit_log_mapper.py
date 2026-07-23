"""Chuyển đổi giữa ORM model và domain entity của nhật ký kiểm toán."""

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.infrastructure.models.audit_log_model import AuditLogModel


class AuditLogMapper:
    """Cầu nối giữa bảng ``audit_logs`` và entity ``AuditLog``.

    Không có ``update_model``: nhật ký chỉ được ghi thêm.
    """

    @staticmethod
    def to_domain(model: AuditLogModel) -> AuditLog:
        return AuditLog(
            id=model.id,
            action=AuditAction(model.action),
            actor_id=model.actor_id,
            resource_type=model.resource_type,
            resource_id=model.resource_id,
            changes=model.changes,
            ip_address=model.ip_address,
            user_agent=model.user_agent,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: AuditLog) -> AuditLogModel:
        return AuditLogModel(
            id=entity.id,
            action=entity.action.value,
            actor_id=entity.actor_id,
            resource_type=entity.resource_type,
            resource_id=entity.resource_id,
            changes=entity.changes,
            ip_address=entity.ip_address,
            user_agent=entity.user_agent,
            created_at=entity.created_at,
        )
