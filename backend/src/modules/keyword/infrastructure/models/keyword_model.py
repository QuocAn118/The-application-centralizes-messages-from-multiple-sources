"""ORM model cho bảng từ khoá."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class KeywordModel(Base):
    """Bảng ``keywords``.

    ``department_id`` là UUID thuần tham chiếu identity, cố ý không khoá ngoại để
    giữ module keyword độc lập. ``normalized`` là dạng bỏ dấu/thường hoá của
    ``text``; unique theo (department_id, normalized) chốt "một từ khoá chỉ có một
    lần trong một phòng" ngay ở tầng DB, khớp với kiểm tra chống trùng ở use case.
    """

    __tablename__ = "keywords"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    department_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    text: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "uq_keyword_department_normalized",
            "department_id",
            "normalized",
            unique=True,
        ),
        Index("ix_keyword_department_id", "department_id"),
    )
