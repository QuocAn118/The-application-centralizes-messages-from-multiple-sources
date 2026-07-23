"""ORM model cho bảng phòng ban."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class DepartmentModel(Base):
    """Bảng ``departments``.

    Chỉ mô tả cấu trúc bảng — mọi quy tắc nghiệp vụ nằm ở
    ``domain.entities.department.Department``.
    """

    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("uq_department_name", func.lower(name), unique=True),
        Index("ix_department_is_active", "is_active"),
    )
