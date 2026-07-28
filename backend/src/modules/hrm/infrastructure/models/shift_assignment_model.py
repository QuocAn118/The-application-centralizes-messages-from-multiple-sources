"""ORM model cho bảng phân ca."""

from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Time, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class ShiftAssignmentModel(Base):
    """Bảng ``shift_assignments``.

    ``shift_id`` là khoá ngoại nội bộ trong module hrm (cùng module — cho phép).
    ``user_id``/``department_id`` là UUID thuần tham chiếu identity, không khoá
    ngoại. Khung giờ chụp lại từ mẫu ca lúc phân để kiểm chồng ca không phải
    nạp lại Shift và để lịch sử ổn định. Index ``(user_id, work_date)`` phục vụ
    truy vấn chồng ca.
    """

    __tablename__ = "shift_assignments"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    shift_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("shifts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    department_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    end_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'CANCELLED')",
            name="ck_shift_assignment_status_hop_le",
        ),
        CheckConstraint("end_time > start_time", name="ck_shift_assignment_window_hop_le"),
        # Kiểm chồng ca: lọc theo nhân viên + ngày.
        Index("ix_shift_assignment_user_date", "user_id", "work_date"),
        Index("ix_shift_assignment_department_id", "department_id"),
        Index("ix_shift_assignment_shift_id", "shift_id"),
    )
