"""ORM model cho bảng ``conversation_events`` — timeline dòng hệ thống (BE-2)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class ConversationEventModel(Base):
    """Một sự kiện nhận/giao/đổi/gỡ người phụ trách. Người tham chiếu qua UUID."""

    __tablename__ = "conversation_events"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    from_user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    to_user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('TAKEN','AUTO_ASSIGNED','ASSIGNED','REASSIGNED','UNASSIGNED')",
            name="ck_conversation_event_kind",
        ),
        Index("ix_conversation_event_conv_created", "conversation_id", "created_at"),
    )
