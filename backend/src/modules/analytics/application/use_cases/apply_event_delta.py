"""Use case incremental: cộng một sự kiện vào rollup ngày (dùng bởi hook).

Hook ở ``analytics.infrastructure`` dịch một sự kiện của #1 sang ``EventKind``
trung lập + bối cảnh (ngày local, phòng, nhân viên, kênh, giây), rồi gọi use case
này. Use case dựng đúng "delta" và cộng vào bảng rollup qua ``IRollupRepository``.

Không ném lỗi nghiệp vụ: nếu thiếu bối cảnh bắt buộc cho một loại (ví dụ CLOSED
mà không có ``user_id``), bỏ qua phần agent — rollup khối lượng vẫn cộng được.
Tách lỗi hạ tầng là việc của hook (nuốt lỗi) — xem RB-1.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from src.modules.analytics.domain.ports import EventKind, IRollupRepository
from src.modules.analytics.domain.value_objects.metrics import (
    DailyAgentMetric,
    DailyConversationMetric,
)


@dataclass(frozen=True)
class EventContext:
    """Bối cảnh một sự kiện để quy về đúng dòng rollup.

    ``work_date`` đã là **ngày nghiệp vụ địa phương của CHÍNH SỰ KIỆN** (hook quy
    đổi theo ``app_timezone`` trước khi gọi — RB-5). Quy tắc gắn ngày là
    **event-time**: ngày của hành động (tin khách / tin trả lời đầu / lúc đóng),
    KHÔNG phải ngày mở hội thoại — để backfill (``IConversationStatsSource``) khớp
    ở ca qua nửa đêm. ``channel_platform`` cần cho rollup khối lượng;
    ``user_id``/``department_id`` cho rollup hiệu suất. ``seconds`` là thời gian
    phản hồi (OUTBOUND đầu) hoặc xử lý (CLOSED) khi có.
    """

    work_date: date
    channel_platform: str = ""
    department_id: UUID | None = None
    user_id: UUID | None = None
    seconds: int | None = None


class ApplyEventDelta:
    """Cộng một sự kiện vào rollup ngày tương ứng."""

    def __init__(self, rollup_repo: IRollupRepository) -> None:
        self._rollup_repo = rollup_repo

    async def execute(self, kind: EventKind, ctx: EventContext) -> None:
        conv = self._delta_khoi_luong(kind, ctx)
        if conv is not None:
            await self._rollup_repo.bump_conversation(conv)

        agent = self._delta_hieu_suat(kind, ctx)
        if agent is not None:
            await self._rollup_repo.bump_agent(agent)

    def _delta_khoi_luong(
        self, kind: EventKind, ctx: EventContext
    ) -> DailyConversationMetric | None:
        """Delta cho ``analytics_daily_conversation`` (nếu loại sự kiện có ảnh hưởng)."""
        inbound = 1 if kind is EventKind.INBOUND else 0
        outbound = 1 if kind is EventKind.OUTBOUND else 0
        opened = 1 if kind is EventKind.OPENED else 0
        closed = 1 if kind is EventKind.CLOSED else 0
        if not (inbound or outbound or opened or closed):
            return None
        return DailyConversationMetric(
            work_date=ctx.work_date,
            department_id=ctx.department_id,
            channel_platform=ctx.channel_platform,
            inbound_count=inbound,
            outbound_count=outbound,
            opened_count=opened,
            closed_count=closed,
        )

    def _delta_hieu_suat(self, kind: EventKind, ctx: EventContext) -> DailyAgentMetric | None:
        """Delta cho ``analytics_daily_agent`` — chỉ khi có ``user_id``.

        - ``CLOSED``: +1 handled; nếu có ``seconds`` thì +1 mẫu resolution.
        - ``OUTBOUND``: nếu có ``seconds`` (tin trả lời ĐẦU của hội thoại) thì +1
          mẫu first_response — hook chỉ gửi ``seconds`` cho tin đầu.
        - ``ASSIGNED``: +1 assigned.
        Các loại khác / không có user → không đụng rollup agent.
        """
        if ctx.user_id is None:
            return None

        handled = fr_sum = fr_n = res_sum = res_n = assigned = 0
        if kind is EventKind.CLOSED:
            handled = 1
            if ctx.seconds is not None:
                res_sum, res_n = ctx.seconds, 1
        elif kind is EventKind.OUTBOUND:
            if ctx.seconds is None:
                return None  # tin trả lời không phải tin đầu → không có mẫu phản hồi
            fr_sum, fr_n = ctx.seconds, 1
        elif kind is EventKind.ASSIGNED:
            assigned = 1
        else:
            return None

        return DailyAgentMetric(
            work_date=ctx.work_date,
            user_id=ctx.user_id,
            department_id=ctx.department_id,
            handled_count=handled,
            assigned_count=assigned,
            sum_first_response_seconds=fr_sum,
            first_response_samples=fr_n,
            sum_resolution_seconds=res_sum,
            resolution_samples=res_n,
        )
