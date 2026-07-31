"""Xác nhận fake khớp đúng hợp đồng port của analytics.

Nếu một port đổi chữ ký mà fake không theo, phép gán dưới đây làm mypy đỏ.
"""

from src.modules.analytics.domain.ports import (
    IConversationStatsSource,
    IRequestStatsSource,
    IRollupRepository,
    IWorkforceStatsSource,
)
from tests.unit.analytics.fakes import (
    FakeConversationStatsSource,
    FakeRequestStatsSource,
    FakeRollupRepository,
    FakeWorkforceStatsSource,
)


def test_fake_khop_hop_dong_port() -> None:
    _rollup: IRollupRepository = FakeRollupRepository()
    _conv: IConversationStatsSource = FakeConversationStatsSource()
    _workforce: IWorkforceStatsSource = FakeWorkforceStatsSource()
    _request: IRequestStatsSource = FakeRequestStatsSource()
    assert all(obj is not None for obj in (_rollup, _conv, _workforce, _request))
