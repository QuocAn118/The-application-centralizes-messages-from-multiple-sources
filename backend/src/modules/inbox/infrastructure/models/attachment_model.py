"""ORM model cho bảng tệp đính kèm."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class AttachmentModel(Base):
    """Bảng ``attachments``.

    ``stored_path`` trỏ tới bản đã tải về lưu lại; ``original_url`` chỉ để truy
    vết nguồn (URL nền tảng đã hết hạn). Xem RB-4.
    """

    __tablename__ = "attachments"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    message_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "kind IN ('IMAGE', 'FILE')",
            name="ck_attachment_kind_hop_le",
        ),
        Index("ix_attachment_message_id", "message_id"),
    )
