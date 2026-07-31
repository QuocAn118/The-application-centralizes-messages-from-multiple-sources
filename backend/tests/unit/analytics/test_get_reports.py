"""Test 4 report use case: nhóm/gộp đúng + phân quyền (Manager ép phòng, Staff chặn)."""

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from src.modules.analytics.application.actor import ActorRole, AnalyticsActor
from src.modules.analytics.application.use_cases.get_reports import (
    GetAgentReport,
    GetConversationReport,
    GetRequestReport,
    GetWorkforceReport,
)
from src.modules.analytics.domain.ports import RequestRow, WorkforceRow
from src.modules.analytics.domain.value_objects.metrics import (
    DailyAgentMetric,
    DailyConversationMetric,
    DateRange,
)
from src.shared.application.exceptions import PermissionDeniedError
from tests.unit.analytics.fakes import (
    FakeRequestStatsSource,
    FakeRollupRepository,
    FakeWorkforceStatsSource,
)

NGAY = date(2026, 7, 1)
KHOANG = DateRange(date(2026, 7, 1), date(2026, 7, 31))
D1 = UUID("00000000-0000-0000-0000-0000000000d1")
D2 = UUID("00000000-0000-0000-0000-0000000000d2")
U1 = UUID("00000000-0000-0000-0000-0000000000a1")
U2 = UUID("00000000-0000-0000-0000-0000000000a2")

ADMIN = AnalyticsActor(user_id=UUID(int=1), role=ActorRole.ADMIN)
MANAGER_D1 = AnalyticsActor(user_id=UUID(int=2), role=ActorRole.MANAGER, department_id=D1)
STAFF = AnalyticsActor(user_id=UUID(int=3), role=ActorRole.STAFF, department_id=D1)


async def _seed_conv(repo: FakeRollupRepository) -> None:
    await repo.bump_conversation(
        DailyConversationMetric(
            work_date=NGAY, department_id=D1, channel_platform="ZALO", inbound_count=5
        )
    )
    await repo.bump_conversation(
        DailyConversationMetric(
            work_date=NGAY, department_id=D2, channel_platform="ZALO", inbound_count=9
        )
    )


class TestConversationReport:
    async def test_admin_thay_moi_phong_nhom_theo_phong_kenh(self) -> None:
        repo = FakeRollupRepository()
        await _seed_conv(repo)
        ket_qua = await GetConversationReport(repo).execute(ADMIN, KHOANG, None)
        phong = {r.department_id for r in ket_qua}
        assert phong == {D1, D2}

    async def test_manager_chi_thay_phong_minh_du_truyen_phong_khac(self) -> None:
        repo = FakeRollupRepository()
        await _seed_conv(repo)
        # Manager D1 cố xem D2 → vẫn chỉ ra D1.
        ket_qua = await GetConversationReport(repo).execute(MANAGER_D1, KHOANG, D2)
        assert [r.department_id for r in ket_qua] == [D1]
        assert ket_qua[0].volume.inbound_count == 5

    async def test_staff_bi_chan(self) -> None:
        repo = FakeRollupRepository()
        with pytest.raises(PermissionDeniedError):
            await GetConversationReport(repo).execute(STAFF, KHOANG, None)


class TestAgentReport:
    async def test_manager_chi_thay_nhan_vien_phong_minh(self) -> None:
        repo = FakeRollupRepository()
        await repo.bump_agent(
            DailyAgentMetric(work_date=NGAY, user_id=U1, department_id=D1, handled_count=3)
        )
        await repo.bump_agent(
            DailyAgentMetric(work_date=NGAY, user_id=U2, department_id=D2, handled_count=7)
        )
        ket_qua = await GetAgentReport(repo).execute(MANAGER_D1, KHOANG, None)
        assert [p.user_id for p in ket_qua] == [U1]

    async def test_staff_bi_chan(self) -> None:
        repo = FakeRollupRepository()
        with pytest.raises(PermissionDeniedError):
            await GetAgentReport(repo).execute(STAFF, KHOANG, None)


class TestWorkforceReport:
    async def test_admin_doc_thang_nguon_4(self) -> None:
        rows = (
            WorkforceRow(
                user_id=U1,
                department_id=D1,
                shift_count=20,
                worked_seconds=576000,
                kpi_percent=Decimal("80"),
                period="2026-07",
            ),
            WorkforceRow(
                user_id=U2,
                department_id=D2,
                shift_count=18,
                worked_seconds=518400,
                kpi_percent=None,
                period="2026-07",
            ),
        )
        source = FakeWorkforceStatsSource(rows)
        ket_qua = await GetWorkforceReport(source).execute(MANAGER_D1, KHOANG, None)
        assert [r.user_id for r in ket_qua] == [U1]  # ép phòng D1


class TestRequestReport:
    async def test_manager_ep_phong_minh(self) -> None:
        rows = (
            RequestRow(
                department_id=D1,
                request_type="NGHI_PHEP",
                status="DA_DUYET",
                count=4,
                sum_decision_seconds=3600,
                decided_samples=4,
            ),
            RequestRow(
                department_id=D2,
                request_type="NGHI_PHEP",
                status="CHO_DUYET",
                count=2,
                sum_decision_seconds=0,
                decided_samples=0,
            ),
        )
        source = FakeRequestStatsSource(rows)
        ket_qua = await GetRequestReport(source).execute(MANAGER_D1, KHOANG, None)
        assert [r.department_id for r in ket_qua] == [D1]

    async def test_staff_bi_chan(self) -> None:
        source = FakeRequestStatsSource(())
        with pytest.raises(PermissionDeniedError):
            await GetRequestReport(source).execute(STAFF, KHOANG, None)
