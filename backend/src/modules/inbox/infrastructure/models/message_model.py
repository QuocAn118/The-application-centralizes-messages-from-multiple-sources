"""ORM model cho bảng tin nhắn."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class MessageModel(Base):
    """Bảng ``messages``.

    ``external_message_id`` chỉ có ở tin đến và là chốt idempotency: unique để
    hai webhook trùng không tạo hai tin. ``sender_user_id`` là UUID thuần (tin
    đi), không khoá ngoại sang identity.
    """

    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender_user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "direction IN ('INBOUND', 'OUTBOUND')",
            name="ck_message_direction_hop_le",
        ),
        # Idempotency webhook: mỗi external_message_id chỉ xử lý một lần. Partial
        # để nhiều tin đi (external_message_id NULL) không đụng ràng buộc.
        Index(
            "uq_message_external_id",
            "external_message_id",
            unique=True,
            postgresql_where=sql_text("external_message_id IS NOT NULL"),
        ),
        Index("ix_message_conversation_id", "conversation_id", "created_at"),
    )
