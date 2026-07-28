"""ORM model cho bảng mục tiêu KPI."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class KpiTargetModel(Base):
    """Bảng ``kpi_targets``.

    ``subject_id`` là user hoặc department (tuỳ ``subject_type``), UUID thuần
    không khoá ngoại. ``department_id`` chụp phòng của đối tượng lúc đặt để
    Manager liệt kê được mọi mục tiêu trong phòng mình (cấp phòng lẫn cấp nhân
    viên). Kỳ giữ ở dạng (năm, tháng). Unique trên bộ khoá đối tượng+chỉ số+kỳ
    để một đối tượng chỉ có một mục tiêu cho mỗi chỉ số mỗi kỳ.
    """

    __tablename__ = "kpi_targets"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    department_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    metric_type: Mapped[str] = mapped_column(String(40), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    target_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "subject_type IN ('USER', 'DEPARTMENT')",
            name="ck_kpi_target_subject_type_hop_le",
        ),
        CheckConstraint(
            "period_month BETWEEN 1 AND 12",
            name="ck_kpi_target_month_hop_le",
        ),
        CheckConstraint("target_value >= 0", name="ck_kpi_target_value_khong_am"),
        # Một đối tượng chỉ có một mục tiêu cho mỗi chỉ số mỗi kỳ.
        Index(
            "uq_kpi_target_subject_metric_period",
            "subject_type",
            "subject_id",
            "metric_type",
            "period_year",
            "period_month",
            unique=True,
        ),
        Index("ix_kpi_target_department_id", "department_id"),
    )
