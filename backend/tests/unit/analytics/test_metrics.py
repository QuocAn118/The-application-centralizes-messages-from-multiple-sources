"""Test value object số liệu — bất biến (frozen), mặc định, và DateRange."""

from datetime import date
from uuid import UUID

import pytest

from src.modules.analytics.domain.value_objects.metrics import (
    AgentPerformance,
    ConversationVolume,
    DailyAgentMetric,
    DailyConversationMetric,
    DateRange,
)
from src.shared.application.exceptions import ApplicationError

U = UUID("00000000-0000-0000-0000-0000000000a1")
D = UUID("00000000-0000-0000-0000-0000000000d1")


class TestDateRange:
    def test_hop_le_khi_from_nho_hon_hoac_bang_to(self) -> None:
        r = DateRange(from_date=date(2026, 7, 1), to_date=date(2026, 7, 31))
        assert r.from_date == date(2026, 7, 1)

    def test_bang_nhau_van_hop_le(self) -> None:
        r = DateRange(from_date=date(2026, 7, 1), to_date=date(2026, 7, 1))
        assert r.from_date == r.to_date

    def test_from_lon_hon_to_thi_loi(self) -> None:
        with pytest.raises(ApplicationError) as e:
            DateRange(from_date=date(2026, 7, 31), to_date=date(2026, 7, 1))
        assert e.value.code == "ANALYTICS_INVALID_DATE_RANGE"


class TestDailyMetrics:
    def test_conversation_mac_dinh_0(self) -> None:
        m = DailyConversationMetric(
            work_date=date(2026, 7, 1), department_id=D, channel_platform="ZALO"
        )
        assert (m.inbound_count, m.outbound_count, m.opened_count, m.closed_count) == (0, 0, 0, 0)

    def test_conversation_department_none_hop_le(self) -> None:
        m = DailyConversationMetric(
            work_date=date(2026, 7, 1), department_id=None, channel_platform="ZALO", inbound_count=3
        )
        assert m.department_id is None
        assert m.inbound_count == 3

    def test_agent_mac_dinh_0(self) -> None:
        m = DailyAgentMetric(work_date=date(2026, 7, 1), user_id=U)
        assert m.handled_count == 0
        assert m.first_response_samples == 0

    def test_frozen_khong_sua_duoc(self) -> None:
        m = DailyConversationMetric(
            work_date=date(2026, 7, 1), department_id=D, channel_platform="ZALO"
        )
        with pytest.raises(AttributeError):
            m.inbound_count = 5  # type: ignore[misc]


class TestReportVO:
    def test_avg_none_khi_khong_co_mau(self) -> None:
        p = AgentPerformance(
            user_id=U,
            handled_count=0,
            assigned_count=0,
            avg_first_response_seconds=None,
            avg_resolution_seconds=None,
        )
        assert p.avg_first_response_seconds is None

    def test_volume_giu_dung_gia_tri(self) -> None:
        v = ConversationVolume(inbound_count=10, outbound_count=8, opened_count=4, closed_count=3)
        assert (v.inbound_count, v.closed_count) == (10, 3)
