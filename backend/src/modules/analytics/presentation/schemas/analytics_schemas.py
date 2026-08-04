"""Schema HTTP cho báo cáo analytics (JSON đọc-chỉ cho dashboard FE)."""

from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.analytics.application.use_cases.get_reports import (
    ConversationReportRow,
)
from src.modules.analytics.domain.ports import RequestRow, WorkforceRow
from src.modules.analytics.domain.value_objects.metrics import AgentPerformance


class ConversationReportItem(BaseModel):
    """Khối lượng một phòng theo kênh trong khoảng báo cáo."""

    department_id: UUID | None
    channel_platform: str
    inbound_count: int
    outbound_count: int
    opened_count: int
    closed_count: int

    @classmethod
    def from_row(cls, r: ConversationReportRow) -> "ConversationReportItem":
        return cls(
            department_id=r.department_id,
            channel_platform=r.channel_platform,
            inbound_count=r.volume.inbound_count,
            outbound_count=r.volume.outbound_count,
            opened_count=r.volume.opened_count,
            closed_count=r.volume.closed_count,
        )


class AgentReportItem(BaseModel):
    """Hiệu suất một nhân viên trong khoảng báo cáo."""

    user_id: UUID
    handled_count: int
    assigned_count: int
    avg_first_response_seconds: float | None
    avg_resolution_seconds: float | None

    @classmethod
    def from_performance(cls, p: AgentPerformance) -> "AgentReportItem":
        return cls(
            user_id=p.user_id,
            handled_count=p.handled_count,
            assigned_count=p.assigned_count,
            avg_first_response_seconds=p.avg_first_response_seconds,
            avg_resolution_seconds=p.avg_resolution_seconds,
        )


class WorkforceReportItem(BaseModel):
    """Ca làm + KPI một nhân viên/phòng."""

    user_id: UUID
    department_id: UUID | None
    shift_count: int
    worked_seconds: int
    kpi_percent: float | None
    period: str | None

    @classmethod
    def from_row(cls, r: WorkforceRow) -> "WorkforceReportItem":
        return cls(
            user_id=r.user_id,
            department_id=r.department_id,
            shift_count=r.shift_count,
            worked_seconds=r.worked_seconds,
            kpi_percent=float(r.kpi_percent) if r.kpi_percent is not None else None,
            period=r.period,
        )


class RequestReportItem(BaseModel):
    """Đơn từ theo phòng/loại/trạng thái + thời gian duyệt."""

    department_id: UUID | None
    request_type: str
    status: str
    count: int
    avg_decision_seconds: float | None

    @classmethod
    def from_row(cls, r: RequestRow) -> "RequestReportItem":
        avg = r.sum_decision_seconds / r.decided_samples if r.decided_samples > 0 else None
        return cls(
            department_id=r.department_id,
            request_type=r.request_type,
            status=r.status,
            count=r.count,
            avg_decision_seconds=avg,
        )


class RebuildResponse(BaseModel):
    """Kết quả chạy backfill: số ngày đã dựng lại."""

    days_rebuilt: int = Field(..., ge=0)
