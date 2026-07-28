"""ORM model cho bảng đơn từ."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class RequestModel(Base):
    """Bảng ``requests``.

    ``requester_id``/``department_id``/``decided_by`` là UUID thuần tham chiếu
    identity — không khoá ngoại. ``department_id`` chụp lúc gửi để định tuyến
    người duyệt và giữ lịch sử ổn định. ``leave_start``/``leave_end`` chỉ có ở
    đơn nghỉ phép. Đơn ở trạng thái cuối là bất biến (đảm bảo ở domain).
    """

    __tablename__ = "requests"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    requester_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    department_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    request_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    leave_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    leave_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    decided_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "request_type IN ('NGHI_PHEP', 'TANG_LUONG', 'KHAC')",
            name="ck_request_type_hop_le",
        ),
        CheckConstraint(
            "status IN ('CHO_DUYET', 'DA_DUYET', 'TU_CHOI', 'DA_HUY')",
            name="ck_request_status_hop_le",
        ),
        Index("ix_request_requester_id", "requester_id"),
        Index("ix_request_department_id", "department_id"),
        Index("ix_request_status", "status"),
    )
