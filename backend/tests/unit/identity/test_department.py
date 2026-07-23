from datetime import UTC, datetime

import pytest

from src.modules.identity.domain.entities.department import (
    Department,
    DepartmentHasActiveMembersError,
    EmptyDepartmentNameError,
)

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
SAU_DO = datetime(2026, 7, 21, 11, 0, tzinfo=UTC)


def _tao_phong_ban(ten: str = "Tư vấn sản phẩm A") -> Department:
    return Department.create(name=ten, description=None, now=BAY_GIO)


class TestTaoPhongBan:
    def test_phong_ban_moi_o_trang_thai_hoat_dong(self) -> None:
        phong = _tao_phong_ban()

        assert phong.is_active is True
        assert phong.name == "Tư vấn sản phẩm A"
        assert phong.created_at == BAY_GIO
        assert phong.updated_at == BAY_GIO

    def test_cat_khoang_trang_thua_trong_ten(self) -> None:
        assert _tao_phong_ban("  Kinh doanh  ").name == "Kinh doanh"

    @pytest.mark.parametrize("ten_sai", ["", "   ", "\t\n"])
    def test_tu_choi_ten_rong(self, ten_sai: str) -> None:
        with pytest.raises(EmptyDepartmentNameError):
            _tao_phong_ban(ten_sai)


class TestDoiTenPhongBan:
    def test_doi_ten_cap_nhat_ca_moc_thoi_gian(self) -> None:
        phong = _tao_phong_ban()

        phong.rename("Chăm sóc khách hàng", now=SAU_DO)

        assert phong.name == "Chăm sóc khách hàng"
        assert phong.updated_at == SAU_DO

    def test_tu_choi_doi_sang_ten_rong(self) -> None:
        phong = _tao_phong_ban()

        with pytest.raises(EmptyDepartmentNameError):
            phong.rename("   ", now=SAU_DO)


class TestVoHieuHoaPhongBan:
    def test_vo_hieu_hoa_duoc_khi_khong_con_nhan_vien(self) -> None:
        phong = _tao_phong_ban()

        phong.deactivate(active_member_count=0, now=SAU_DO)

        assert phong.is_active is False
        assert phong.updated_at == SAU_DO

    def test_tu_choi_khi_con_nhan_vien_dang_hoat_dong(self) -> None:
        phong = _tao_phong_ban()

        with pytest.raises(DepartmentHasActiveMembersError):
            phong.deactivate(active_member_count=3, now=SAU_DO)

        assert phong.is_active is True

    def test_vo_hieu_hoa_lai_lan_nua_khong_gay_loi(self) -> None:
        phong = _tao_phong_ban()
        phong.deactivate(active_member_count=0, now=SAU_DO)

        phong.deactivate(active_member_count=0, now=SAU_DO)

        assert phong.is_active is False
