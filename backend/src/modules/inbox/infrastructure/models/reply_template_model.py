"""ORM model cho ``reply_templates`` (BE-7)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class ReplyTemplateModel(Base):
    """Phòng tham chiếu qua UUID; ``null`` = mẫu dùng chung."""

    __tablename__ = "reply_templates"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    department_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_reply_template_phong", "department_id"),)
