"""Unit test cho domain service ``tinh_phan_tram_kpi`` (chiều chỉ số KPI)."""

from decimal import Decimal

from src.modules.hrm.domain.services.kpi_achievement import tinh_phan_tram_kpi
from src.modules.hrm.domain.value_objects.kpi import KpiMetricType


class TestTinhPhanTramKpi:
    def test_cao_la_tot_thuc_dat_tren_muc_tieu(self) -> None:
        # CONVERSATIONS_CLOSED: đóng 8/10 mục tiêu → 80%.
        pt = tinh_phan_tram_kpi(
            KpiMetricType.CONVERSATIONS_CLOSED, Decimal(10), Decimal(8)
        )
        assert pt == Decimal("80.0")

    def test_cao_la_tot_vuot_muc_tieu_tren_100(self) -> None:
        pt = tinh_phan_tram_kpi(
            KpiMetricType.CONVERSATIONS_CLOSED, Decimal(10), Decimal(12)
        )
        assert pt == Decimal("120.0")

    def test_thap_la_tot_nhanh_hon_tren_100(self) -> None:
        # AVG_RESPONSE_MINUTES: mục tiêu 10 phút, thực đạt 5 → nhanh gấp đôi → 200%.
        pt = tinh_phan_tram_kpi(
            KpiMetricType.AVG_RESPONSE_MINUTES, Decimal(10), Decimal(5)
        )
        assert pt == Decimal("200.0")

    def test_thuc_dat_none_tra_none(self) -> None:
        assert (
            tinh_phan_tram_kpi(KpiMetricType.CONVERSATIONS_CLOSED, Decimal(10), None)
            is None
        )

    def test_mau_so_khong_tra_none(self) -> None:
        # cao-là-tốt với target 0 → không xác định.
        assert (
            tinh_phan_tram_kpi(KpiMetricType.CONVERSATIONS_CLOSED, Decimal(0), Decimal(5))
            is None
        )
        # thấp-là-tốt với actual 0 → không xác định.
        assert (
            tinh_phan_tram_kpi(KpiMetricType.AVG_RESPONSE_MINUTES, Decimal(10), Decimal(0))
            is None
        )
