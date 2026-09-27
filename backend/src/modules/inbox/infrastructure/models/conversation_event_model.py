"""ORM model cho bảng ``conversation_events`` — timeline dòng hệ thống (BE-2)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class ConversationEventModel(Base):
    """Một sự kiện nhận/giao/đổi/gỡ người phụ trách hoặc phân phòng. Tham chiếu qua UUID."""

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
    department_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('TAKEN','AUTO_ASSIGNED','ASSIGNED','REASSIGNED','UNASSIGNED',"
            "'DEPARTMENT_ASSIGNED','AUTO_ROUTED')",
            name="ck_conversation_event_kind",
        ),
        Index("ix_conversation_event_conv_created", "conversation_id", "created_at"),
    )
