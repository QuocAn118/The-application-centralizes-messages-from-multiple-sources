"""DTO đọc cho tầng application của hrm.

Dạng dữ liệu use case trả cho presentation — thuần dữ liệu, bất biến. Tách khỏi
entity để router không phụ thuộc vào chi tiết domain và để KPI progress gộp sẵn
mục tiêu với thực đạt.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.modules.hrm.domain.value_objects.request_kind import (
    RequestStatus,
    RequestType,
)


@dataclass(frozen=True)
class Page[T]:
    """Một trang kết quả cùng tổng số bản ghi khớp bộ lọc."""

    items: list[T]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class ShiftView:
    """Một mẫu ca."""

    id: UUID
    department_id: UUID
    name: str
    start_time: time
    end_time: time
    is_active: bool


@dataclass(frozen=True)
class ShiftAssignmentView:
    """Một buổi phân ca."""

    id: UUID
    shift_id: UUID
    user_id: UUID
    department_id: UUID
    work_date: date
    start_time: time
    end_time: time
    status: str


@dataclass(frozen=True)
class KpiTargetView:
    """Một mục tiêu KPI đã đặt."""

    id: UUID
    subject_type: KpiSubjectType
    subject_id: UUID
    metric_type: KpiMetricType
    period: KpiPeriod
    target_value: Decimal


@dataclass(frozen=True)
class KpiProgressView:
    """Tiến độ KPI: mục tiêu ghép với thực đạt và % hoàn thành.

    ``actual`` là ``None`` khi nguồn hiệu suất chưa có dữ liệu cho đối tượng/kỳ
    đó (khác với 0). ``achievement_percent`` cũng ``None`` khi không tính được;
    ngoài ra nó đã tính đúng theo *chiều* của chỉ số (chỉ số "càng thấp càng
    tốt" như thời gian phản hồi được tính ngược).
    """

    subject_type: KpiSubjectType
    subject_id: UUID
    metric_type: KpiMetricType
    period: KpiPeriod
    target_value: Decimal
    actual_value: Decimal | None
    achievement_percent: Decimal | None


@dataclass(frozen=True)
class RequestView:
    """Một đơn từ kèm kết quả quyết định (nếu đã có)."""

    id: UUID
    requester_id: UUID
    department_id: UUID
    request_type: RequestType
    reason: str
    status: RequestStatus
    created_at: datetime
    leave_start: date | None = None
    leave_end: date | None = None
    decided_by: UUID | None = None
    decided_at: datetime | None = None
    decision_reason: str | None = None
