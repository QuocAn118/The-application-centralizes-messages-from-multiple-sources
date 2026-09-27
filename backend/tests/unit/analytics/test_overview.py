"""BE-8: ``GetOverview`` — 4 thẻ KPI + xu hướng theo ngày."""

from datetime import date

import pytest

from src.modules.analytics.application.actor import ActorRole, AnalyticsActor
from src.modules.analytics.application.use_cases.get_reports import GetOverview
from src.modules.analytics.domain.value_objects.metrics import (
    DailyAgentMetric,
    DailyConversationMetric,
    DateRange,
)
from src.shared.application.exceptions import PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.analytics.fakes import FakeResponseRateSource, FakeRollupRepository

PHONG_A = new_id()
PHONG_B = new_id()
KHOANG = DateRange(from_date=date(2026, 9, 1), to_date=date(2026, 9, 5))


def _admin() -> AnalyticsActor:
    return AnalyticsActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)


def _manager(dept=PHONG_A) -> AnalyticsActor:  # type: ignore[no-untyped-def]
    return AnalyticsActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=dept)


async def _repo() -> FakeRollupRepository:
    repo = FakeRollupRepository()
    for ngay, dept, vao, ra, dong in (
        (date(2026, 9, 1), PHONG_A, 5, 3, 1),
        (date(2026, 9, 1), PHONG_B, 7, 0, 0),
        (date(2026, 9, 4), PHONG_A, 2, 2, 2),
        (date(2026, 8, 31), PHONG_A, 99, 99, 99),  # ngoài khoảng
    ):
        await repo.bump_conversation(
            DailyConversationMetric(
                work_date=ngay,
                department_id=dept,
                channel_platform="ZALO",
                inbound_count=vao,
                outbound_count=ra,
                closed_count=dong,
            )
        )
    u = new_id()
    # Ngày 1: 1 mẫu 100s; ngày 4: 3 mẫu tổng 180s -> có trọng số 280/4 = 70
    # (trung bình của trung bình sẽ sai thành (100 + 60) / 2 = 80).
    await repo.bump_agent(
        DailyAgentMetric(
            work_date=date(2026, 9, 1),
            user_id=u,
            department_id=PHONG_A,
            sum_first_response_seconds=100,
            first_response_samples=1,
        )
    )
    await repo.bump_agent(
        DailyAgentMetric(
            work_date=date(2026, 9, 4),
            user_id=u,
            department_id=PHONG_A,
            sum_first_response_seconds=180,
            first_response_samples=3,
        )
    )
    return repo


class TestGetOverview:
    async def test_tong_va_xu_huong_du_moi_ngay(self) -> None:
        kq = await GetOverview(await _repo(), FakeResponseRateSource(4, 3)).execute(
            _admin(), KHOANG, None
        )
        assert kq.totals.inbound_count == 14
        assert kq.totals.outbound_count == 5
        assert kq.totals.closed_count == 3
        # Đủ 5 ngày, ngày trống = 0 (biểu đồ không nhảy cóc).
        assert [d.work_date.day for d in kq.daily] == [1, 2, 3, 4, 5]
        assert [d.volume.inbound_count for d in kq.daily] == [12, 0, 0, 2, 0]

    async def test_thoi_gian_phan_hoi_trung_binh_co_trong_so(self) -> None:
        kq = await GetOverview(await _repo(), FakeResponseRateSource()).execute(
            _admin(), KHOANG, None
        )
        assert kq.avg_first_response_seconds == 70
        assert kq.first_response_samples == 4

    async def test_ti_le_phan_hoi(self) -> None:
        kq = await GetOverview(await _repo(), FakeResponseRateSource(4, 3)).execute(
            _admin(), KHOANG, None
        )
        assert kq.response_rate == 0.75
        assert (kq.conversations_with_inbound, kq.conversations_replied) == (4, 3)

    async def test_khong_co_tin_vao_thi_ti_le_la_none_khong_phai_0(self) -> None:
        kq = await GetOverview(FakeRollupRepository(), FakeResponseRateSource(0, 0)).execute(
            _admin(), KHOANG, None
        )
        assert kq.response_rate is None
        assert kq.avg_first_response_seconds is None

    async def test_manager_bi_ep_ve_phong_minh(self) -> None:
        nguon = FakeResponseRateSource(1, 1)
        kq = await GetOverview(await _repo(), nguon).execute(_manager(PHONG_A), KHOANG, PHONG_B)
        assert kq.totals.inbound_count == 7  # chỉ phòng A (5 + 2), bỏ qua PHONG_B truyền vào
        assert nguon.pham_vi_da_hoi == [(PHONG_A,)]

    async def test_staff_bi_chan(self) -> None:
        staff = AnalyticsActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)
        with pytest.raises(PermissionDeniedError):
            await GetOverview(FakeRollupRepository(), FakeResponseRateSource()).execute(
                staff, KHOANG, None
            )
