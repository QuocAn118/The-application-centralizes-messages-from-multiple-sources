"""Use case đọc 4 báo cáo tổng hợp theo phạm vi quyền.

- ``GetConversationReport`` / ``GetAgentReport``: đọc bảng rollup của #5.
- ``GetWorkforceReport`` / ``GetRequestReport``: đọc THẲNG #4 qua port (dữ liệu #4
  vốn đã tổng hợp) — không rollup.

Mọi báo cáo: ``bao_dam_xem_bao_cao`` (Manager/Admin) rồi ``pham_vi_phong_bao_cao``
ép Manager về phòng mình (RB-4). Kết quả nhóm/gộp qua ``domain.services.aggregation``.
"""

from dataclasses import dataclass
from uuid import UUID

from src.modules.analytics.application.actor import AnalyticsActor
from src.modules.analytics.application.authorization import (
    bao_dam_xem_bao_cao,
    pham_vi_phong_bao_cao,
)
from src.modules.analytics.domain.ports import (
    IRequestStatsSource,
    IRollupRepository,
    IWorkforceStatsSource,
    RequestRow,
    WorkforceRow,
)
from src.modules.analytics.domain.services.aggregation import (
    gop_hieu_suat_nhan_vien,
    gop_khoi_luong,
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
