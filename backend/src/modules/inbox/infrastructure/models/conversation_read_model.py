"""ORM model cho bảng ``conversation_reads`` — đã đọc tới đâu, theo từng người (BE-1)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class ConversationReadModel(Base):
    """Một dòng cho mỗi (người, hội thoại) đã từng mở.

    Tin VÀO có ``created_at > last_read_at`` là chưa đọc; không có dòng = chưa đọc
    tin nào. ``user_id`` không khoá ngoại sang identity (tham chiếu qua UUID).
    """

    __tablename__ = "conversation_reads"

    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
