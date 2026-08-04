"""Test RebuildDailyRollup: ghi đè từng ngày từ nguồn, idempotent."""

from datetime import date
from uuid import UUID

from src.modules.analytics.application.use_cases.rebuild_daily_rollup import (
    RebuildDailyRollup,
)
from src.modules.analytics.domain.value_objects.metrics import (
    DailyAgentMetric,
    DailyConversationMetric,
    DateRange,
)
from tests.unit.analytics.fakes import FakeConversationStatsSource, FakeRollupRepository

D = UUID("00000000-0000-0000-0000-0000000000d1")
U = UUID("00000000-0000-0000-0000-0000000000a1")


async def test_rebuild_ghi_de_tung_ngay() -> None:
    ngay1, ngay2 = date(2026, 7, 1), date(2026, 7, 2)
    source = FakeConversationStatsSource(
        conv_by_day={
            ngay1: (
                DailyConversationMetric(
                    work_date=ngay1, department_id=D, channel_platform="ZALO", inbound_count=5
                ),
            ),
            ngay2: (
                DailyConversationMetric(
                    work_date=ngay2, department_id=D, channel_platform="ZALO", inbound_count=3
                ),
            ),
        },
        agent_by_day={
            ngay1: (
                DailyAgentMetric(work_date=ngay1, user_id=U, department_id=D, handled_count=2),
            ),
        },
    )
    repo = FakeRollupRepository()
    so_ngay = await RebuildDailyRollup(source, repo).execute(DateRange(ngay1, ngay2))
    assert so_ngay == 2
    assert sum(m.inbound_count for m in repo.conv.values()) == 8
    assert sum(a.handled_count for a in repo.agent.values()) == 2


async def test_rebuild_idempotent_ghi_de_khong_cong_don() -> None:
    ngay = date(2026, 7, 1)
    source = FakeConversationStatsSource(
        conv_by_day={
            ngay: (
                DailyConversationMetric(
                    work_date=ngay, department_id=D, channel_platform="ZALO", inbound_count=5
                ),
            ),
        }
    )
    repo = FakeRollupRepository()
    khoang = DateRange(ngay, ngay)
    await RebuildDailyRollup(source, repo).execute(khoang)
    await RebuildDailyRollup(source, repo).execute(khoang)  # chạy lại
    # Ghi đè (không cộng dồn) → vẫn 5, không phải 10.
    assert sum(m.inbound_count for m in repo.conv.values()) == 5


async def test_rebuild_nguon_rong_van_ghi_de_xoa_so_cu() -> None:
    ngay = date(2026, 7, 1)
    repo = FakeRollupRepository()
    # Có số cũ sai từ trước.
    await repo.bump_conversation(
        DailyConversationMetric(
            work_date=ngay, department_id=D, channel_platform="ZALO", inbound_count=99
        )
    )
    source = FakeConversationStatsSource()  # nguồn rỗng cho ngày này
    await RebuildDailyRollup(source, repo).execute(DateRange(ngay, ngay))
    assert repo.conv == {}  # đã bị ghi đè rỗng
