from dataclasses import FrozenInstanceError

import pytest

from src.modules.identity.domain.value_objects.email import (
    DO_DAI_EMAIL_TOI_DA,
    Email,
    EmailTooLongError,
    InvalidEmailError,
)
from src.modules.identity.domain.value_objects.password_hash import (
    InvalidPasswordHashError,
    PasswordHash,
)
from src.modules.identity.domain.value_objects.role import Role


class TestEmail:
    def test_chap_nhan_email_hop_le(self) -> None:
        assert Email("nhanvien@congty.vn").value == "nhanvien@congty.vn"

    def test_chuyen_ve_chu_thuong(self) -> None:
        assert Email("NhanVien@CongTy.VN").value == "nhanvien@congty.vn"

    def test_cat_khoang_trang_thua(self) -> None:
        assert Email("  a@b.vn  ").value == "a@b.vn"

    @pytest.mark.parametrize(
        "gia_tri_sai",
        ["", "   ", "khong-co-a-cong", "@thieu-phan-dau.vn", "thieu-duoi@", "a@b", "a b@c.vn"],
    )
    def test_tu_choi_email_sai_dinh_dang(self, gia_tri_sai: str) -> None:
        with pytest.raises(InvalidEmailError):
            Email(gia_tri_sai)

    def test_hai_email_cung_gia_tri_thi_bang_nhau(self) -> None:
        assert Email("a@b.vn") == Email("A@B.VN")

    def test_chap_nhan_email_dung_bang_gioi_han(self) -> None:
        phan_dau = "a" * (DO_DAI_EMAIL_TOI_DA - len("@congty.vn"))
        dung_gioi_han = f"{phan_dau}@congty.vn"

        assert len(Email(dung_gioi_han).value) == DO_DAI_EMAIL_TOI_DA

    def test_tu_choi_email_vuot_gioi_han(self) -> None:
        """Cột ``users.email`` là VARCHAR(320) — domain phải chặn trước khi
        cơ sở dữ liệu ném DataError khó truy nguyên."""
        qua_dai = "a" * (DO_DAI_EMAIL_TOI_DA - len("@congty.vn") + 1) + "@congty.vn"

        with pytest.raises(EmailTooLongError):
            Email(qua_dai)

    def test_khong_the_thay_doi_sau_khi_tao(self) -> None:
        email = Email("a@b.vn")
        with pytest.raises(FrozenInstanceError):
            email.value = "c@d.vn"  # type: ignore[misc]


class TestRole:
    def test_co_dung_ba_vai_tro(self) -> None:
        assert {r.value for r in Role} == {"STAFF", "MANAGER", "ADMIN"}

    @pytest.mark.parametrize("vai_tro", [Role.STAFF, Role.MANAGER])
    def test_staff_va_manager_bat_buoc_thuoc_phong_ban(self, vai_tro: Role) -> None:
        assert vai_tro.requires_department() is True

    def test_admin_khong_thuoc_phong_ban_nao(self) -> None:
        assert Role.ADMIN.requires_department() is False

    def test_so_sanh_duoc_voi_chuoi(self) -> None:
        assert Role.STAFF == "STAFF"


class TestPasswordHash:
    def test_giu_nguyen_chuoi_hash(self) -> None:
        chuoi = "$2b$12$abcdefghijklmnopqrstuv"
        assert PasswordHash(chuoi).value == chuoi

    @pytest.mark.parametrize("gia_tri_sai", ["", "   "])
    def test_tu_choi_chuoi_rong(self, gia_tri_sai: str) -> None:
        with pytest.raises(InvalidPasswordHashError):
            PasswordHash(gia_tri_sai)

    def test_khong_lo_hash_khi_in_ra(self) -> None:
        """Hash không được xuất hiện trong log hay thông báo lỗi."""
        hash_that = "$2b$12$chuoi_hash_bi_mat"
        assert hash_that not in repr(PasswordHash(hash_that))
