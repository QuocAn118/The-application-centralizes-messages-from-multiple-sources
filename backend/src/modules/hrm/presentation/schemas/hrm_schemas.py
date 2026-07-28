"""Schema Pydantic cho các endpoint hrm.

Chỉ mô tả dữ liệu vào/ra HTTP; nghiệp vụ nằm ở use case. Các ``*Response`` dựng
từ DTO của tầng application để router không lộ entity domain ra ngoài.
"""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.hrm.application.dto.hrm_dto import (
    KpiProgressView,
    KpiTargetView,
    RequestView,
    ShiftAssignmentView,
    ShiftView,
)
from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiSubjectType,
)
from src.modules.hrm.domain.value_objects.request_kind import RequestStatus, RequestType

# ----- Shift -----


class CreateShiftRequest(BaseModel):
    department_id: UUID
    name: str = Field(min_length=1, max_length=200)
    start_time: time
    end_time: time


class UpdateShiftRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    start_time: time
    end_time: time


class ShiftResponse(BaseModel):
    id: UUID
    department_id: UUID
    name: str
    start_time: time
    end_time: time
    is_active: bool

    @classmethod
    def from_view(cls, v: ShiftView) -> "ShiftResponse":
        return cls(
            id=v.id,
            department_id=v.department_id,
            name=v.name,
            start_time=v.start_time,
            end_time=v.end_time,
            is_active=v.is_active,
        )


# ----- Shift assignment -----


class AssignShiftRequest(BaseModel):
    shift_id: UUID
    user_id: UUID
    work_date: date


class ShiftAssignmentResponse(BaseModel):
    id: UUID
    shift_id: UUID
    user_id: UUID
    department_id: UUID
    work_date: date
    start_time: time
    end_time: time
    status: str

    @classmethod
    def from_view(cls, v: ShiftAssignmentView) -> "ShiftAssignmentResponse":
        return cls(
            id=v.id,
            shift_id=v.shift_id,
            user_id=v.user_id,
            department_id=v.department_id,
            work_date=v.work_date,
            start_time=v.start_time,
            end_time=v.end_time,
            status=v.status,
        )


# ----- KPI -----


class SetKpiTargetRequest(BaseModel):
    subject_type: KpiSubjectType
    subject_id: UUID
    metric_type: KpiMetricType
    period_year: int = Field(ge=1)
    period_month: int = Field(ge=1, le=12)
    target_value: Decimal = Field(ge=0)


class KpiTargetResponse(BaseModel):
    id: UUID
    subject_type: KpiSubjectType
    subject_id: UUID
    department_id: UUID
    metric_type: KpiMetricType
    period_year: int
    period_month: int
    target_value: Decimal

    @classmethod
    def from_view(cls, v: KpiTargetView) -> "KpiTargetResponse":
        return cls(
            id=v.id,
            subject_type=v.subject_type,
            subject_id=v.subject_id,
            department_id=v.department_id,
            metric_type=v.metric_type,
            period_year=v.period.year,
            period_month=v.period.month,
            target_value=v.target_value,
        )


class KpiProgressResponse(BaseModel):
    subject_type: KpiSubjectType
    subject_id: UUID
    metric_type: KpiMetricType
    period_year: int
    period_month: int
    target_value: Decimal
    actual_value: Decimal | None
    achievement_percent: Decimal | None

    @classmethod
    def from_view(cls, v: KpiProgressView) -> "KpiProgressResponse":
        return cls(
            subject_type=v.subject_type,
            subject_id=v.subject_id,
            metric_type=v.metric_type,
            period_year=v.period.year,
            period_month=v.period.month,
            target_value=v.target_value,
            actual_value=v.actual_value,
            achievement_percent=v.achievement_percent,
        )


# ----- Request (đơn từ) -----


class SubmitRequestRequest(BaseModel):
    request_type: RequestType
    reason: str = Field(min_length=1)
    leave_start: date | None = None
    leave_end: date | None = None


class RejectRequestRequest(BaseModel):
    reason: str = Field(min_length=1)


class RequestResponse(BaseModel):
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

    @classmethod
    def from_view(cls, v: RequestView) -> "RequestResponse":
        return cls(
            id=v.id,
            requester_id=v.requester_id,
            department_id=v.department_id,
            request_type=v.request_type,
            reason=v.reason,
            status=v.status,
            created_at=v.created_at,
            leave_start=v.leave_start,
            leave_end=v.leave_end,
            decided_by=v.decided_by,
            decided_at=v.decided_at,
            decision_reason=v.decision_reason,
        )


class PageResponse[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int
