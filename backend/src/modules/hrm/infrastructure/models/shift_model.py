"""ORM model cho bảng mẫu ca."""

from datetime import datetime, time
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Time, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class ShiftModel(Base):
    """Bảng ``shifts``.

    ``department_id`` là UUID thuần tham chiếu identity — cố ý **không** khoá
    ngoại sang ``departments`` để giữ module hrm độc lập. ``end_time`` luôn sau
    ``start_time`` (ca không qua nửa đêm ở #4) — ràng buộc ở cả CHECK lẫn domain.
    """

    __tablename__ = "shifts"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    department_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    start_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    end_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_shift_window_hop_le"),
        Index("ix_shift_department_id", "department_id"),
        Index("ix_shift_is_active", "is_active"),
    )
