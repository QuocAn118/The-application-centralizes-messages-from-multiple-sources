"""ORM model cho ``customer_notes`` — ghi chú nội bộ theo phòng (BE-5)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class CustomerNoteModel(Base):
    """Người viết + phòng tham chiếu qua UUID (không khoá ngoại sang identity)."""

    __tablename__ = "customer_notes"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    department_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    author_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_customer_note_khach_phong", "customer_id", "department_id", "created_at"),
    )
