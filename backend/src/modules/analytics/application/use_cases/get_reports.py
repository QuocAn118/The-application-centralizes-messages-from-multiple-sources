"""Use case đọc 4 báo cáo tổng hợp theo phạm vi quyền.

- ``GetConversationReport`` / ``GetAgentReport``: đọc bảng rollup của #5.
- ``GetWorkforceReport`` / ``GetRequestReport``: đọc THẲNG #4 qua port (dữ liệu #4
  vốn đã tổng hợp) — không rollup.

Mọi báo cáo: ``bao_dam_xem_bao_cao`` (Manager/Admin) rồi ``pham_vi_phong_bao_cao``
ép Manager về phòng mình (RB-4). Kết quả nhóm/gộp qua ``domain.services.aggregation``.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from src.modules.analytics.application.actor import AnalyticsActor
from src.modules.analytics.application.authorization import (
    bao_dam_xem_bao_cao,
    pham_vi_phong_bao_cao,
)
from src.modules.analytics.domain.ports import (
    IRequestStatsSource,
    IResponseRateSource,
    IRollupRepository,
    IWorkforceStatsSource,
    RequestRow,
    WorkforceRow,
)
from src.modules.analytics.domain.services.aggregation import (
    gop_hieu_suat_nhan_vien,
    gop_khoi_luong,
    trung_binh,
)
from src.modules.analytics.domain.value_objects.metrics import (
    AgentPerformance,
    ConversationVolume,
    DailyConversationMetric,
    DateRange,
)


@dataclass(frozen=True)
class ConversationReportRow:
    """Một dòng báo cáo khối lượng: một phòng theo kênh, đã gộp trong khoảng."""

    department_id: UUID | None
    channel_platform: str
    volume: ConversationVolume


class GetConversationReport:
    """Khối lượng tin/hội thoại, nhóm theo (phòng, kênh)."""

    def __init__(self, rollup_repo: IRollupRepository) -> None:
        self._rollup_repo = rollup_repo

    async def execute(
        self, actor: AnalyticsActor, khoang: DateRange, department_id: UUID | None
    ) -> tuple[ConversationReportRow, ...]:
        bao_dam_xem_bao_cao(actor)
        pham_vi = pham_vi_phong_bao_cao(actor, department_id)
        rows = await self._rollup_repo.doc_conversation(khoang, pham_vi)

        # Nhóm theo (phòng, kênh) giữ thứ tự xuất hiện đầu tiên → tất định.
        thu_tu: list[tuple[UUID | None, str]] = []
        gom: dict[tuple[UUID | None, str], list[DailyConversationMetric]] = {}
        for r in rows:
            key = (r.department_id, r.channel_platform)
            if key not in gom:
                gom[key] = []
                thu_tu.append(key)
            gom[key].append(r)

        return tuple(
            ConversationReportRow(
                department_id=dept,
                channel_platform=kenh,
                volume=gop_khoi_luong(gom[(dept, kenh)]),
            )
            for dept, kenh in thu_tu
        )


class GetAgentReport:
    """Hiệu suất theo nhân viên, gộp trong khoảng."""

    def __init__(self, rollup_repo: IRollupRepository) -> None:
        self._rollup_repo = rollup_repo

    async def execute(
        self, actor: AnalyticsActor, khoang: DateRange, department_id: UUID | None
    ) -> tuple[AgentPerformance, ...]:
        bao_dam_xem_bao_cao(actor)
        pham_vi = pham_vi_phong_bao_cao(actor, department_id)
        rows = await self._rollup_repo.doc_agent(khoang, pham_vi)
        return gop_hieu_suat_nhan_vien(rows)


@dataclass(frozen=True)
class DailyVolume:
    """Khối lượng một ngày (mọi phòng/kênh trong phạm vi đã cộng lại)."""

    work_date: date
    volume: ConversationVolume


@dataclass(frozen=True)
class OverviewReport:
    """Tổng quan báo cáo hội thoại (BE-8): 4 thẻ KPI + xu hướng theo ngày.

    ``avg_first_response_seconds`` là trung bình **có trọng số** (tổng giây / tổng
    mẫu của cả khoảng) — không lấy trung bình của các trung bình ngày.
    ``response_rate`` ∈ [0, 1]; ``None`` khi kỳ không có hội thoại nào có tin vào
    (không phải 0%: không có gì để trả lời thì chưa đo được).
    ``daily`` có ĐỦ mọi ngày trong khoảng, ngày trống = 0 — biểu đồ không nhảy cóc.
    """

    totals: ConversationVolume
    avg_first_response_seconds: float | None
    first_response_samples: int
    response_rate: float | None
    conversations_with_inbound: int
    conversations_replied: int
    daily: tuple[DailyVolume, ...]


class GetOverview:
    """Tổng quan cho tab Hội thoại: rollup (#5) + đếm hội thoại thẳng từ #1."""

    def __init__(
        self, rollup_repo: IRollupRepository, response_source: IResponseRateSource
    ) -> None:
        self._rollup_repo = rollup_repo
        self._response_source = response_source

    async def execute(
        self, actor: AnalyticsActor, khoang: DateRange, department_id: UUID | None
    ) -> OverviewReport:
        bao_dam_xem_bao_cao(actor)
        pham_vi = pham_vi_phong_bao_cao(actor, department_id)

        rows = await self._rollup_repo.doc_conversation(khoang, pham_vi)
        agent_rows = await self._rollup_repo.doc_agent(khoang, pham_vi)
        dem = await self._response_source.dem_phan_hoi(khoang, pham_vi)

        theo_ngay: dict[date, list[DailyConversationMetric]] = {}
        for r in rows:
            theo_ngay.setdefault(r.work_date, []).append(r)
        so_ngay = (khoang.to_date - khoang.from_date).days + 1
        daily = tuple(
            DailyVolume(work_date=d, volume=gop_khoi_luong(theo_ngay.get(d, ())))
            for d in (khoang.from_date + timedelta(days=i) for i in range(so_ngay))
        )

        fr_tong = sum(a.sum_first_response_seconds for a in agent_rows)
        fr_mau = sum(a.first_response_samples for a in agent_rows)
        return OverviewReport(
            totals=gop_khoi_luong(rows),
            avg_first_response_seconds=trung_binh(fr_tong, fr_mau),
            first_response_samples=fr_mau,
            response_rate=(dem.da_tra_loi / dem.co_tin_vao) if dem.co_tin_vao else None,
            conversations_with_inbound=dem.co_tin_vao,
            conversations_replied=dem.da_tra_loi,
            daily=daily,
        )


class GetWorkforceReport:
    """Ca làm + KPI theo nhân viên/phòng — đọc thẳng #4."""

    def __init__(self, source: IWorkforceStatsSource) -> None:
        self._source = source

    async def execute(
        self, actor: AnalyticsActor, khoang: DateRange, department_id: UUID | None
    ) -> tuple[WorkforceRow, ...]:
        bao_dam_xem_bao_cao(actor)
        pham_vi = pham_vi_phong_bao_cao(actor, department_id)
        return await self._source.workforce_rows(khoang, pham_vi)


class GetRequestReport:
    """Đơn từ theo loại/trạng thái — đọc thẳng #4."""

    def __init__(self, source: IRequestStatsSource) -> None:
        self._source = source

    async def execute(
        self, actor: AnalyticsActor, khoang: DateRange, department_id: UUID | None
    ) -> tuple[RequestRow, ...]:
        bao_dam_xem_bao_cao(actor)
        pham_vi = pham_vi_phong_bao_cao(actor, department_id)
        return await self._source.request_rows(khoang, pham_vi)
