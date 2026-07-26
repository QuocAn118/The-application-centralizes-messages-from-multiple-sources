"""Entity mục tiêu KPI — chỉ tiêu Manager đặt cho nhân viên/phòng theo kỳ."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import BusinessRuleViolationError


class NegativeKpiTargetError(BusinessRuleViolationError):
    """Giá trị mục tiêu KPI không được âm."""

    def __init__(self) -> None:
        super().__init__(
            "Giá trị mục tiêu KPI không được âm.",
            code="NEGATIVE_KPI_TARGET",
        )


@dataclass(eq=False, kw_only=True)
class KpiTarget(AggregateRoot):
    """Chỉ tiêu cho một đối tượng (nhân viên hoặc phòng) trong một kỳ (tháng).

    Chỉ giữ *mục tiêu* Manager đặt; giá trị **thực đạt** không lưu ở đây mà tính
    khi cần từ nguồn hiệu suất (Inbox) qua port. ``subject_id`` là UUID thuần
    (user hoặc department tuỳ ``subject_type``), không khoá ngoại sang identity.
    """

    subject_type: KpiSubjectType
    subject_id: UUID
    metric_type: KpiMetricType
    period: KpiPeriod
    target_value: Decimal
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def _kiem_tra(target_value: Decimal) -> None:
        if target_value < 0:
            raise NegativeKpiTargetError

    @classmethod
    def set_target(
        cls,
        subject_type: KpiSubjectType,
        subject_id: UUID,
        metric_type: KpiMetricType,
        period: KpiPeriod,
        target_value: Decimal,
        now: datetime,
    ) -> "KpiTarget":
        """Đặt một mục tiêu KPI mới."""
        cls._kiem_tra(target_value)
        return cls(
            subject_type=subject_type,
            subject_id=subject_id,
            metric_type=metric_type,
            period=period,
            target_value=target_value,
            created_at=now,
            updated_at=now,
        )

    def change_target(self, target_value: Decimal, now: datetime) -> None:
        """Cập nhật giá trị mục tiêu, giữ nguyên đối tượng/chỉ số/kỳ."""
        self._kiem_tra(target_value)
        self.target_value = target_value
        self.updated_at = now
