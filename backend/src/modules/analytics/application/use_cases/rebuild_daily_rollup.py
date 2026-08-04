"""Use case backfill: dựng lại rollup một khoảng ngày từ bảng nguồn #1.

Quét nguồn (``IConversationStatsSource``) tính lại toàn bộ dòng rollup của mỗi
ngày rồi **ghi đè tuyệt đối** (không cộng dồn lên số cũ) — đây là nguồn sự thật
để đối chiếu/sửa lệch khi incremental lỡ sự kiện. Idempotent: chạy lại nhiều lần
cho cùng khoảng ngày ra cùng kết quả.

Dùng khi: khởi tạo #5 trên dữ liệu cũ, hook lỡ sự kiện, hoặc số liệu nghi lệch.
"""

from datetime import timedelta

from src.modules.analytics.domain.ports import (
    IConversationStatsSource,
    IRollupRepository,
)
from src.modules.analytics.domain.value_objects.metrics import DateRange


class RebuildDailyRollup:
    """Ghi đè rollup #1 cho từng ngày trong khoảng, tính lại từ nguồn."""

    def __init__(
        self,
        stats_source: IConversationStatsSource,
        rollup_repo: IRollupRepository,
    ) -> None:
        self._stats_source = stats_source
        self._rollup_repo = rollup_repo

    async def execute(self, khoang: DateRange) -> int:
        """Dựng lại từng ngày trong khoảng; trả số ngày đã xử lý."""
        so_ngay = 0
        ngay = khoang.from_date
        while ngay <= khoang.to_date:
            conv = await self._stats_source.conversation_metrics_cho_ngay(ngay)
            agent = await self._stats_source.agent_metrics_cho_ngay(ngay)
            # Ghi đè tuyệt đối: kể cả khi nguồn rỗng vẫn ghi đè để xoá số cũ sai.
            await self._rollup_repo.ghi_de_conversation_ngay(ngay, conv)
            await self._rollup_repo.ghi_de_agent_ngay(ngay, agent)
            so_ngay += 1
            ngay += timedelta(days=1)
        return so_ngay
