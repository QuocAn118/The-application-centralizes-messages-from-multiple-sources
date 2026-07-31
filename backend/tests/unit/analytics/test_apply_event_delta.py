"""Test ApplyEventDelta: cộng đúng delta vào rollup theo từng loại sự kiện."""

from datetime import date
from uuid import UUID

from src.modules.analytics.application.use_cases.apply_event_delta import (
    ApplyEventDelta,
    EventContext,
)
from src.modules.analytics.domain.ports import EventKind
from tests.unit.analytics.fakes import FakeRollupRepository

NGAY = date(2026, 7, 15)
U = UUID("00000000-0000-0000-0000-0000000000a1")
D = UUID("00000000-0000-0000-0000-0000000000d1")


async def test_inbound_cong_khoi_luong() -> None:
    repo = FakeRollupRepository()
    await ApplyEventDelta(repo).execute(
        EventKind.INBOUND, EventContext(work_date=NGAY, channel_platform="ZALO", department_id=D)
    )
    (m,) = repo.conv.values()
    assert m.inbound_count == 1
    assert m.outbound_count == 0
    # Không có user → không đụng rollup agent.
    assert repo.agent == {}


async def test_hai_inbound_cong_don() -> None:
    repo = FakeRollupRepository()
    for _ in range(2):
        await ApplyEventDelta(repo).execute(
            EventKind.INBOUND, EventContext(work_date=NGAY, channel_platform="ZALO")
        )
    (m,) = repo.conv.values()
    assert m.inbound_count == 2


async def test_closed_cong_handled_va_resolution_khi_co_user_va_seconds() -> None:
    repo = FakeRollupRepository()
    await ApplyEventDelta(repo).execute(
        EventKind.CLOSED,
        EventContext(
            work_date=NGAY, channel_platform="ZALO", department_id=D, user_id=U, seconds=120
        ),
    )
    (conv,) = repo.conv.values()
    assert conv.closed_count == 1
    (ag,) = repo.agent.values()
    assert ag.handled_count == 1
    assert ag.department_id == D
    assert ag.sum_resolution_seconds == 120
    assert ag.resolution_samples == 1


async def test_closed_khong_seconds_thi_handled_nhung_khong_mau_resolution() -> None:
    repo = FakeRollupRepository()
    await ApplyEventDelta(repo).execute(
        EventKind.CLOSED, EventContext(work_date=NGAY, user_id=U, department_id=D)
    )
    (ag,) = repo.agent.values()
    assert ag.handled_count == 1
    assert ag.resolution_samples == 0


async def test_outbound_dau_co_seconds_thi_mau_first_response() -> None:
    repo = FakeRollupRepository()
    await ApplyEventDelta(repo).execute(
        EventKind.OUTBOUND,
        EventContext(
            work_date=NGAY, channel_platform="ZALO", department_id=D, user_id=U, seconds=45
        ),
    )
    (conv,) = repo.conv.values()
    assert conv.outbound_count == 1
    (ag,) = repo.agent.values()
    assert ag.sum_first_response_seconds == 45
    assert ag.first_response_samples == 1


async def test_outbound_khong_seconds_thi_khong_mau_agent() -> None:
    repo = FakeRollupRepository()
    await ApplyEventDelta(repo).execute(
        EventKind.OUTBOUND,
        EventContext(work_date=NGAY, channel_platform="ZALO", user_id=U),
    )
    # Vẫn cộng outbound khối lượng, nhưng không mẫu first_response.
    (conv,) = repo.conv.values()
    assert conv.outbound_count == 1
    assert repo.agent == {}


async def test_assigned_cong_assigned_count() -> None:
    repo = FakeRollupRepository()
    await ApplyEventDelta(repo).execute(
        EventKind.ASSIGNED, EventContext(work_date=NGAY, user_id=U, department_id=D)
    )
    # ASSIGNED không phải sự kiện khối lượng.
    assert repo.conv == {}
    (ag,) = repo.agent.values()
    assert ag.assigned_count == 1
