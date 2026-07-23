from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.modules.identity.domain.entities.user import (
    AdminCannotHaveDepartmentError,
    CannotChangeToAdminError,
    DepartmentAlreadyHasManagerError,
    DepartmentRequiredError,
    EmptyFullNameError,
    InactiveDepartmentError,
    LastAdminCannotBeDeactivatedError,
    User,
)
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
SAU_DO = datetime(2026, 7, 21, 11, 0, tzinfo=UTC)
HASH_MAU = PasswordHash("$2b$12$hash_gia_lap")
PHONG_A: UUID = new_id()
PHONG_B: UUID = new_id()


def _tao_user(
    role: Role = Role.STAFF,
    department_id: UUID | None = PHONG_A,
    email: str = "nhanvien@congty.vn",
) -> User:
    return User.create(
        email=Email(email),
        password_hash=HASH_MAU,
        full_name="Nguyễn Văn A",
        role=role,
        department_id=department_id,
        now=BAY_GIO,
    )


class TestTaoUser:
    def test_staff_moi_o_trang_thai_hoat_dong_va_phai_doi_mat_khau(self) -> None:
        user = _tao_user()

        assert user.is_active is True
        assert user.must_change_password is True
        assert user.last_login_at is None
        assert user.department_id == PHONG_A

    def test_admin_khong_gan_phong_ban(self) -> None:
        admin = _tao_user(role=Role.ADMIN, department_id=None)

        assert admin.department_id is None

    @pytest.mark.parametrize("vai_tro", [Role.STAFF, Role.MANAGER])
    def test_staff_va_manager_thieu_phong_ban_thi_bi_tu_choi(self, vai_tro: Role) -> None:
        with pytest.raises(DepartmentRequiredError):
            _tao_user(role=vai_tro, department_id=None)

    def test_admin_co_phong_ban_thi_bi_tu_choi(self) -> None:
        with pytest.raises(AdminCannotHaveDepartmentError):
            _tao_user(role=Role.ADMIN, department_id=PHONG_A)

    @pytest.mark.parametrize("ten_sai", ["", "   "])
    def test_tu_choi_ho_ten_rong(self, ten_sai: str) -> None:
        with pytest.raises(EmptyFullNameError):
            User.create(
                email=Email("a@b.vn"),
                password_hash=HASH_MAU,
                full_name=ten_sai,
                role=Role.STAFF,
                department_id=PHONG_A,
                now=BAY_GIO,
            )


class TestDoiVaiTro:
    def test_staff_len_manager_khi_phong_chua_co_manager(self) -> None:
        user = _tao_user(role=Role.STAFF)

        user.change_role(
            new_role=Role.MANAGER,
            department_id=PHONG_A,
            department_has_active_manager=False,
            now=SAU_DO,
        )

        assert user.role is Role.MANAGER
        assert user.updated_at == SAU_DO

    def test_staff_len_manager_bi_tu_choi_khi_phong_da_co_manager(self) -> None:
        user = _tao_user(role=Role.STAFF)

        with pytest.raises(DepartmentAlreadyHasManagerError):
            user.change_role(
                new_role=Role.MANAGER,
                department_id=PHONG_A,
                department_has_active_manager=True,
                now=SAU_DO,
            )

        assert user.role is Role.STAFF

    def test_manager_xuong_staff_luon_duoc_phep(self) -> None:
        user = _tao_user(role=Role.MANAGER)

        user.change_role(
            new_role=Role.STAFF,
            department_id=PHONG_A,
            department_has_active_manager=True,
            now=SAU_DO,
        )

        assert user.role is Role.STAFF

    def test_khong_the_chuyen_thanh_admin(self) -> None:
        """Đề bài chỉ cho phép chuyển đổi Staff ↔ Manager."""
        user = _tao_user(role=Role.STAFF)

        with pytest.raises(CannotChangeToAdminError):
            user.change_role(
                new_role=Role.ADMIN,
                department_id=None,
                department_has_active_manager=False,
                now=SAU_DO,
            )

    def test_len_manager_o_phong_khac_thi_doi_luon_phong(self) -> None:
        user = _tao_user(role=Role.STAFF, department_id=PHONG_A)

        user.change_role(
            new_role=Role.MANAGER,
            department_id=PHONG_B,
            department_has_active_manager=False,
            now=SAU_DO,
        )

        assert user.department_id == PHONG_B


class TestChuyenPhongBan:
    def test_chuyen_staff_sang_phong_khac(self) -> None:
        user = _tao_user(role=Role.STAFF, department_id=PHONG_A)

        user.assign_to_department(
            department_id=PHONG_B, department_has_active_manager=False, now=SAU_DO
        )

        assert user.department_id == PHONG_B

    def test_chuyen_manager_sang_phong_da_co_manager_thi_bi_tu_choi(self) -> None:
        user = _tao_user(role=Role.MANAGER, department_id=PHONG_A)

        with pytest.raises(DepartmentAlreadyHasManagerError):
            user.assign_to_department(
                department_id=PHONG_B, department_has_active_manager=True, now=SAU_DO
            )

    def test_staff_khong_the_bo_trong_phong_ban(self) -> None:
        user = _tao_user(role=Role.STAFF)

        with pytest.raises(DepartmentRequiredError):
            user.assign_to_department(
                department_id=None, department_has_active_manager=False, now=SAU_DO
            )


class TestVoHieuHoa:
    def test_vo_hieu_hoa_staff(self) -> None:
        user = _tao_user()

        user.deactivate(is_last_active_admin=False, now=SAU_DO)

        assert user.is_active is False

    def test_khong_the_vo_hieu_hoa_admin_cuoi_cung(self) -> None:
        admin = _tao_user(role=Role.ADMIN, department_id=None)

        with pytest.raises(LastAdminCannotBeDeactivatedError):
            admin.deactivate(is_last_active_admin=True, now=SAU_DO)

        assert admin.is_active is True

    def test_vo_hieu_hoa_duoc_admin_khi_con_admin_khac(self) -> None:
        admin = _tao_user(role=Role.ADMIN, department_id=None)

        admin.deactivate(is_last_active_admin=False, now=SAU_DO)

        assert admin.is_active is False


class TestKichHoatLai:
    def test_kich_hoat_lai_staff(self) -> None:
        user = _tao_user()
        user.deactivate(is_last_active_admin=False, now=SAU_DO)

        user.reactivate(
            department_is_active=True, department_has_active_manager=False, now=SAU_DO
        )

        assert user.is_active is True

    def test_tu_choi_khi_phong_ban_da_bi_vo_hieu_hoa(self) -> None:
        user = _tao_user()
        user.deactivate(is_last_active_admin=False, now=SAU_DO)

        with pytest.raises(InactiveDepartmentError):
            user.reactivate(
                department_is_active=False, department_has_active_manager=False, now=SAU_DO
            )

    def test_tu_choi_kich_hoat_manager_khi_phong_da_co_manager_khac(self) -> None:
        manager = _tao_user(role=Role.MANAGER)
        manager.deactivate(is_last_active_admin=False, now=SAU_DO)

        with pytest.raises(DepartmentAlreadyHasManagerError):
            manager.reactivate(
                department_is_active=True, department_has_active_manager=True, now=SAU_DO
            )

    def test_kich_hoat_lai_admin_khong_can_phong_ban(self) -> None:
        admin = _tao_user(role=Role.ADMIN, department_id=None)
        admin.deactivate(is_last_active_admin=False, now=SAU_DO)

        admin.reactivate(
            department_is_active=False, department_has_active_manager=True, now=SAU_DO
        )

        assert admin.is_active is True


class TestMatKhauVaDangNhap:
    def test_dat_mat_khau_moi_tat_co_buoc_doi_mat_khau(self) -> None:
        user = _tao_user()
        hash_moi = PasswordHash("$2b$12$hash_moi")

        user.set_password(hash_moi, must_change=False, now=SAU_DO)

        assert user.password_hash == hash_moi
        assert user.must_change_password is False

    def test_admin_reset_mat_khau_thi_bat_buoc_doi_lai(self) -> None:
        user = _tao_user()
        user.set_password(PasswordHash("$2b$12$tam"), must_change=True, now=SAU_DO)

        assert user.must_change_password is True

    def test_ghi_nhan_lan_dang_nhap(self) -> None:
        user = _tao_user()

        user.record_login(now=SAU_DO)

        assert user.last_login_at == SAU_DO


class TestQuyenQuanLy:
    def test_admin_quan_ly_duoc_moi_nguoi(self) -> None:
        admin = _tao_user(role=Role.ADMIN, department_id=None, email="admin@congty.vn")
        staff = _tao_user(role=Role.STAFF, department_id=PHONG_A)

        assert admin.can_manage(staff) is True

    def test_manager_quan_ly_duoc_staff_cung_phong(self) -> None:
        manager = _tao_user(role=Role.MANAGER, department_id=PHONG_A, email="m@congty.vn")
        staff = _tao_user(role=Role.STAFF, department_id=PHONG_A)

        assert manager.can_manage(staff) is True

    def test_manager_khong_quan_ly_duoc_staff_phong_khac(self) -> None:
        manager = _tao_user(role=Role.MANAGER, department_id=PHONG_A, email="m@congty.vn")
        staff = _tao_user(role=Role.STAFF, department_id=PHONG_B)

        assert manager.can_manage(staff) is False

    def test_manager_khong_quan_ly_duoc_admin(self) -> None:
        manager = _tao_user(role=Role.MANAGER, department_id=PHONG_A, email="m@congty.vn")
        admin = _tao_user(role=Role.ADMIN, department_id=None, email="admin@congty.vn")

        assert manager.can_manage(admin) is False

    def test_manager_khong_quan_ly_duoc_manager_khac_cung_phong(self) -> None:
        """Quản lý chỉ quản được Nhân viên. Không có quyền lên nhau, kể cả cùng
        phòng ban — thiếu test này thì lỗi ``other.role is not Role.ADMIN`` sẽ
        lọt qua và biến can_manage thành lỗ hổng leo thang quyền."""
        manager_a = _tao_user(role=Role.MANAGER, department_id=PHONG_A, email="ma@congty.vn")
        manager_b = _tao_user(role=Role.MANAGER, department_id=PHONG_A, email="mb@congty.vn")

        assert manager_a.can_manage(manager_b) is False

    def test_staff_khong_quan_ly_duoc_ai(self) -> None:
        staff = _tao_user(role=Role.STAFF, department_id=PHONG_A)
        khac = _tao_user(role=Role.STAFF, department_id=PHONG_A, email="b@congty.vn")

        assert staff.can_manage(khac) is False


class TestChanChuyenTuAdmin:
    def test_khong_ha_duoc_admin_xuong_staff(self) -> None:
        """Chỉ chuyển đổi Staff ↔ Manager. Guard tự-chặn của Admin (nhánh
        ``self.role is Role.ADMIN``) chỉ được kiểm chứng bởi test này."""
        admin = _tao_user(role=Role.ADMIN, department_id=None, email="admin@congty.vn")

        with pytest.raises(CannotChangeToAdminError):
            admin.change_role(
                new_role=Role.STAFF,
                department_id=PHONG_A,
                department_has_active_manager=False,
                now=SAU_DO,
            )


class TestCapNhatHoSo:
    def test_cap_nhat_ho_ten_va_so_dien_thoai(self) -> None:
        user = _tao_user()

        user.update_profile(full_name="Tên Mới", phone="0912345678", now=SAU_DO)

        assert user.full_name == "Tên Mới"
        assert user.phone == "0912345678"
        assert user.updated_at == SAU_DO

    def test_tham_so_none_giu_nguyen_gia_tri_cu(self) -> None:
        """``None`` nghĩa là không đổi trường đó — không phải xoá trắng nó."""
        user = _tao_user()
        ho_ten_cu = user.full_name

        user.update_profile(full_name=None, phone="0900000000", now=SAU_DO)

        assert user.full_name == ho_ten_cu
        assert user.phone == "0900000000"

    def test_tu_choi_ho_ten_rong(self) -> None:
        user = _tao_user()

        with pytest.raises(EmptyFullNameError):
            user.update_profile(full_name="   ", phone=None, now=SAU_DO)
