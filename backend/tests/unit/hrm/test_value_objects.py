import pytest

from src.modules.hrm.domain.value_objects.kpi import (
    InvalidKpiPeriodError,
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.modules.hrm.domain.value_objects.request_kind import RequestStatus, RequestType


class TestKpiMetricType:
    def test_co_cac_chi_so_do_duoc(self) -> None:
        assert KpiMetricType.CONVERSATIONS_CLOSED == "CONVERSATIONS_CLOSED"
        assert KpiMetricType.AVG_RESPONSE_MINUTES == "AVG_RESPONSE_MINUTES"

    def test_so_sanh_truc_tiep_voi_chuoi(self) -> None:
        """StrEnum để đọc từ DB và ghi JSON không phải chuyển đổi thủ công."""
        assert KpiMetricType("CONVERSATIONS_CLOSED") is KpiMetricType.CONVERSATIONS_CLOSED


class TestKpiSubjectType:
    def test_ap_cho_nhan_vien_hoac_phong(self) -> None:
        assert KpiSubjectType.USER == "USER"
        assert KpiSubjectType.DEPARTMENT == "DEPARTMENT"


class TestKpiPeriod:
    def test_ky_hop_le(self) -> None:
        ky = KpiPeriod(year=2026, month=8)

        assert ky.year == 2026
        assert ky.month == 8

    def test_la_bat_bien(self) -> None:
        from dataclasses import FrozenInstanceError

        ky = KpiPeriod(year=2026, month=8)
        with pytest.raises(FrozenInstanceError):
            ky.month = 9  # type: ignore[misc]

    @pytest.mark.parametrize("thang", [0, 13, -1, 100])
    def test_thang_ngoai_khoang_bi_tu_choi(self, thang: int) -> None:
        with pytest.raises(InvalidKpiPeriodError):
            KpiPeriod(year=2026, month=thang)

    @pytest.mark.parametrize("nam", [0, -5])
    def test_nam_khong_duong_bi_tu_choi(self, nam: int) -> None:
        with pytest.raises(InvalidKpiPeriodError):
            KpiPeriod(year=nam, month=6)


class TestRequestType:
    def test_co_ba_loai_don_co_dinh(self) -> None:
        assert RequestType.NGHI_PHEP == "NGHI_PHEP"
        assert RequestType.TANG_LUONG == "TANG_LUONG"
        assert RequestType.KHAC == "KHAC"


class TestRequestStatus:
    def test_co_du_bon_trang_thai(self) -> None:
        assert RequestStatus.CHO_DUYET == "CHO_DUYET"
        assert RequestStatus.DA_DUYET == "DA_DUYET"
        assert RequestStatus.TU_CHOI == "TU_CHOI"
        assert RequestStatus.DA_HUY == "DA_HUY"
