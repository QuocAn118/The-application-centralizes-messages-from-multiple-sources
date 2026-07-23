"""ORM model cho bảng refresh token."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class RefreshTokenModel(Base):
    """Bảng ``refresh_tokens``.

    Xoá người dùng thì token bị xoá theo — token không còn ý nghĩa nếu chủ
    của nó không tồn tại.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_refresh_token_user_id", "user_id"),
        Index("ix_refresh_token_expires_at", "expires_at"),
    )
