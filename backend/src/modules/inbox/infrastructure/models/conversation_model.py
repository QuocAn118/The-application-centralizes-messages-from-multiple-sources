"""ORM model cho bảng hội thoại."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, literal_column
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class ConversationModel(Base):
    """Bảng ``conversations``.

    ``department_id``/``assigned_user_id`` là UUID thuần tham chiếu identity —
    không khoá ngoại (spec §8). ``last_message_at`` có index để sort inbox theo
    tin mới nhất.
    """

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    channel_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    assigned_user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('CHO_PHAN', 'DANG_MO', 'DA_DONG')",
            name="ck_conversation_status_hop_le",
        ),
        Index("ix_conversation_channel_id", "channel_id"),
        Index("ix_conversation_customer_id", "customer_id"),
        Index("ix_conversation_department_id", "department_id"),
        Index("ix_conversation_status", "status"),
        # Sort inbox: hội thoại mới nhất lên đầu.
        Index(
            "ix_conversation_last_message_at",
            literal_column("last_message_at DESC"),
        ),
    )
