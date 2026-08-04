"""Cổng (port) mà tầng application của analytics phụ thuộc.

Mọi thứ ở đây là interface + DTO trung lập: implementation nằm ở
``analytics.infrastructure``. Nhờ vậy domain và use case không biết inbox, hrm,
identity tồn tại — chỉ biết các hợp đồng này. Đây là ranh giới giữ analytics độc
lập (nó là hạ nguồn, đọc mọi module nhưng qua port).

Hai nhóm nguồn:
- Rollup #1 (``IRollupRepository`` + ``IConversationStatsSource``): số liệu tin/
  hội thoại/hiệu suất, có bảng rollup riêng của #5 (đọc nhanh) + đường quét nguồn
  để backfill.
- Đọc thẳng #4 (``IWorkforceStatsSource``, ``IRequestStatsSource``): ca/KPI/đơn —
  dữ liệu #4 vốn đã tổng hợp nên đọc trực tiếp, GROUP BY tại query time.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from src.modules.analytics.domain.value_objects.metrics import (
    DailyAgentMetric,
    DailyConversationMetric,
    DateRange,
)


class EventKind(StrEnum):
    """Loại sự kiện incremental mà hook gửi cho ``ApplyEventDelta``.

    Trung lập với module nguồn — hook ở ``analytics.infrastructure`` dịch sự kiện
    của #1 sang loại này rồi mới gọi use case.
    """

    INBOUND = "INBOUND"  # khách gửi một tin → inbound_count += 1
    OUTBOUND = "OUTBOUND"  # nhân viên trả lời một tin → outbound_count += 1
    OPENED = "OPENED"  # hội thoại mới mở (được phân phòng) → opened_count += 1
    CLOSED = "CLOSED"  # hội thoại đóng → closed_count/handled_count += 1
    ASSIGNED = "ASSIGNED"  # hội thoại được gán một nhân viên → assigned_count += 1


@dataclass(frozen=True)
class WorkforceRow:
    """Một dòng số liệu ca + KPI đọc thẳng từ #4 (đã trung lập hoá).

    ``shift_count``/``worked_seconds`` gộp trong khoảng báo cáo; ``kpi_percent``
    là tiến độ KPI kỳ liên quan (``None`` nếu không có target/dữ liệu). ``period``
    ghi rõ kỳ KPI để báo cáo không nhập nhằng.
    """

    user_id: UUID
    department_id: UUID | None
    shift_count: int
    worked_seconds: int
    kpi_percent: Decimal | None
    period: str | None


@dataclass(frozen=True)
class RequestRow:
    """Một dòng số liệu đơn từ đọc thẳng từ #4 (đã trung lập hoá).

    Gộp theo ``(department_id, request_type, status)``; ``sum_decision_seconds``/
    ``decided_samples`` để tính thời gian duyệt trung bình (chỉ đơn đã quyết mới
    vào mẫu).
    """

    department_id: UUID | None
    request_type: str
    status: str
    count: int
    sum_decision_seconds: int
    decided_samples: int


class IRollupRepository(Protocol):
    """Đọc/ghi bảng rollup ngày riêng của #5 (#1 conversation + agent).

    ``bump_*`` cộng-delta (incremental, UPSERT). ``ghi_de_*`` ghi đè tuyệt đối một
    ngày (backfill). ``doc_*`` đọc theo khoảng ngày + lọc phòng.
    """

    async def bump_conversation(self, delta: DailyConversationMetric) -> None: ...

    async def bump_agent(self, delta: DailyAgentMetric) -> None: ...

    async def ghi_de_conversation_ngay(
        self, work_date: date, rows: tuple[DailyConversationMetric, ...]
    ) -> None: ...

    async def ghi_de_agent_ngay(
        self, work_date: date, rows: tuple[DailyAgentMetric, ...]
    ) -> None: ...

    async def doc_conversation(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[DailyConversationMetric, ...]: ...

    async def doc_agent(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[DailyAgentMetric, ...]: ...


class IConversationStatsSource(Protocol):
    """Quét bảng nguồn #1 để dựng lại rollup một ngày (backfill).

    Trả các dòng rollup của đúng ngày ``work_date`` (giờ địa phương) tính lại từ
    tin/hội thoại thật — nguồn sự thật để đối chiếu incremental.

    **HỢP ĐỒNG QUAN TRỌNG — quy tắc gắn ngày (event-time, chốt review GĐ2):** mỗi
    số liệu gắn theo ngày của **hành động sinh ra nó**, KHÔNG phải ngày mở hội
    thoại: ``inbound`` theo ngày tin của khách; ``outbound`` + mẫu first_response
    theo ngày tin trả lời ĐẦU; ``closed``/``handled``/mẫu resolution theo ngày
    ĐÓNG. Implementation PHẢI group theo timestamp (đã quy đổi ``app_timezone``)
    của TỪNG bản ghi nguồn — nếu group theo ngày mở hội thoại, backfill sẽ lệch
    incremental ở ca qua nửa đêm (khách nhắn 23:00 ngày 1, trả lời 01:00 ngày 2 →
    first_response thuộc NGÀY 2). ``ApplyEventDelta`` gắn đúng như vậy vì mỗi hook
    chạy ở thời điểm sự kiện.
    """

    async def conversation_metrics_cho_ngay(
        self, work_date: date
    ) -> tuple[DailyConversationMetric, ...]: ...

    async def agent_metrics_cho_ngay(self, work_date: date) -> tuple[DailyAgentMetric, ...]: ...


class IWorkforceStatsSource(Protocol):
    """Đọc thẳng #4: ca làm + KPI theo nhân viên/phòng trong khoảng báo cáo."""

    async def workforce_rows(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[WorkforceRow, ...]: ...


class IRequestStatsSource(Protocol):
    """Đọc thẳng #4: đơn từ theo loại/trạng thái trong khoảng báo cáo."""

    async def request_rows(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[RequestRow, ...]: ...
