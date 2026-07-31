"""Fake cho các port của analytics — tất định, dùng trong test use case."""

from datetime import date
from uuid import UUID

from src.modules.analytics.domain.ports import (
    RequestRow,
    WorkforceRow,
)
from src.modules.analytics.domain.value_objects.metrics import (
    DailyAgentMetric,
    DailyConversationMetric,
    DateRange,
)


def _loc_phong_conv(
    rows: tuple[DailyConversationMetric, ...], department_ids: tuple[UUID, ...] | None
) -> tuple[DailyConversationMetric, ...]:
    if department_ids is None:
        return rows
    keep = set(department_ids)
    return tuple(r for r in rows if r.department_id in keep)


class FakeRollupRepository:
    """``IRollupRepository`` giả: giữ rollup trong bộ nhớ.

    ``bump_*`` cộng dồn theo khoá tự nhiên; ``ghi_de_*`` thay toàn bộ dòng của một
    ngày; ``doc_*`` lọc theo khoảng ngày + phòng (agent không có phòng nên bỏ qua
    lọc phòng — caller lọc bằng danh sách user).
    """

    def __init__(self) -> None:
        self.conv: dict[tuple[date, UUID | None, str], DailyConversationMetric] = {}
        self.agent: dict[tuple[date, UUID], DailyAgentMetric] = {}

    async def bump_conversation(self, delta: DailyConversationMetric) -> None:
        key = (delta.work_date, delta.department_id, delta.channel_platform)
        cu = self.conv.get(key)
        if cu is None:
            self.conv[key] = delta
            return
        self.conv[key] = DailyConversationMetric(
            work_date=delta.work_date,
            department_id=delta.department_id,
            channel_platform=delta.channel_platform,
            inbound_count=cu.inbound_count + delta.inbound_count,
            outbound_count=cu.outbound_count + delta.outbound_count,
            opened_count=cu.opened_count + delta.opened_count,
            closed_count=cu.closed_count + delta.closed_count,
        )

    async def bump_agent(self, delta: DailyAgentMetric) -> None:
        key = (delta.work_date, delta.user_id)
        cu = self.agent.get(key)
        if cu is None:
            self.agent[key] = delta
            return
        self.agent[key] = DailyAgentMetric(
            work_date=delta.work_date,
            user_id=delta.user_id,
            handled_count=cu.handled_count + delta.handled_count,
            assigned_count=cu.assigned_count + delta.assigned_count,
            sum_first_response_seconds=cu.sum_first_response_seconds
            + delta.sum_first_response_seconds,
            first_response_samples=cu.first_response_samples + delta.first_response_samples,
            sum_resolution_seconds=cu.sum_resolution_seconds + delta.sum_resolution_seconds,
            resolution_samples=cu.resolution_samples + delta.resolution_samples,
        )

    async def ghi_de_conversation_ngay(
        self, work_date: date, rows: tuple[DailyConversationMetric, ...]
    ) -> None:
        self.conv = {k: v for k, v in self.conv.items() if k[0] != work_date}
        for r in rows:
            self.conv[(r.work_date, r.department_id, r.channel_platform)] = r

    async def ghi_de_agent_ngay(self, work_date: date, rows: tuple[DailyAgentMetric, ...]) -> None:
        self.agent = {k: v for k, v in self.agent.items() if k[0] != work_date}
        for r in rows:
            self.agent[(r.work_date, r.user_id)] = r

    async def doc_conversation(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[DailyConversationMetric, ...]:
        trong = tuple(v for k, v in self.conv.items() if khoang.from_date <= k[0] <= khoang.to_date)
        return _loc_phong_conv(trong, department_ids)

    async def doc_agent(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[DailyAgentMetric, ...]:
        # Agent rollup không mang department_id; lọc phòng do use case xử qua danh
        # sách user. Ở fake này bỏ qua department_ids (trả theo khoảng ngày).
        return tuple(v for k, v in self.agent.items() if khoang.from_date <= k[0] <= khoang.to_date)


class FakeConversationStatsSource:
    """``IConversationStatsSource`` giả: trả sẵn metrics theo từng ngày."""

    def __init__(
        self,
        conv_by_day: dict[date, tuple[DailyConversationMetric, ...]] | None = None,
        agent_by_day: dict[date, tuple[DailyAgentMetric, ...]] | None = None,
    ) -> None:
        self._conv = conv_by_day or {}
        self._agent = agent_by_day or {}

    async def conversation_metrics_cho_ngay(
        self, work_date: date
    ) -> tuple[DailyConversationMetric, ...]:
        return self._conv.get(work_date, ())

    async def agent_metrics_cho_ngay(self, work_date: date) -> tuple[DailyAgentMetric, ...]:
        return self._agent.get(work_date, ())


class FakeWorkforceStatsSource:
    """``IWorkforceStatsSource`` giả."""

    def __init__(self, rows: tuple[WorkforceRow, ...] = ()) -> None:
        self._rows = rows

    async def workforce_rows(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[WorkforceRow, ...]:
        if department_ids is None:
            return self._rows
        keep = set(department_ids)
        return tuple(r for r in self._rows if r.department_id in keep)


class FakeRequestStatsSource:
    """``IRequestStatsSource`` giả."""

    def __init__(self, rows: tuple[RequestRow, ...] = ()) -> None:
        self._rows = rows

    async def request_rows(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[RequestRow, ...]:
        if department_ids is None:
            return self._rows
        keep = set(department_ids)
        return tuple(r for r in self._rows if r.department_id in keep)
