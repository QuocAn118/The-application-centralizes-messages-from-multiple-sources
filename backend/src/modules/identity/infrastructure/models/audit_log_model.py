"""ORM model cho bảng nhật ký kiểm toán."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class AuditLogModel(Base):
    """Bảng ``audit_logs`` — chỉ ghi thêm.

    ``actor_id`` dùng ``ON DELETE SET NULL`` chứ không cascade: xoá người dùng
    không được phép làm mất lịch sử hành động của họ.
    """

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    actor_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_log_created_at", created_at.desc()),
        Index("ix_audit_log_actor_id", "actor_id"),
        Index("ix_audit_log_action", "action"),
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
    )
