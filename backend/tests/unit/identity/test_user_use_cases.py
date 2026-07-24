from datetime import UTC, datetime

import pytest

from src.modules.identity.application.use_cases.assign_user_to_department import (
    AssignUserToDepartment,
)
from src.modules.identity.application.use_cases.change_user_role import ChangeUserRole
from src.modules.identity.application.use_cases.create_user import (
    CreateUser,
    EmailAlreadyExistsError,
)
from src.modules.identity.application.use_cases.deactivate_user import DeactivateUser
from src.modules.identity.application.use_cases.get_user import GetUser
from src.modules.identity.application.use_cases.list_users import ListUsers
from src.modules.identity.application.use_cases.reactivate_user import ReactivateUser
from src.modules.identity.application.use_cases.reset_user_password import (
    ResetUserPassword,
)
from src.modules.identity.application.use_cases.update_user import UpdateUser
from src.modules.identity.domain.entities.audit_log import AuditAction
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import (
    DepartmentAlreadyHasManagerError,
    InactiveDepartmentError,
    LastAdminCannotBeDeactivatedError,
    User,
)
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.security.password_hasher import (
    BcryptPasswordHasher,
)
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.identity.fakes import (
    FakeAuditLogRepository,
    FakeClock,
    FakeDepartmentRepository,
    FakeRefreshTokenRepository,
    FakeUserRepository,
)

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


class _BoiCanh:
    """Gom các thành phần dùng chung cho test quản lý người dùng."""

    def __init__(self) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.hasher = BcryptPasswordHasher(rounds=4)
        self.user_repo = FakeUserRepository()
        self.department_repo = FakeDepartmentRepository()
        self.token_repo = FakeRefreshTokenRepository()
        self.audit_repo = FakeAuditLogRepository()

        self.phong_a = Department.create("Phòng A", None, BAY_GIO)
        self.phong_b = Department.create("Phòng B", None, BAY_GIO)
        self.department_repo._departments[self.phong_a.id] = self.phong_a
        self.department_repo._departments[self.phong_b.id] = self.phong_b

    def them(
        self,
        role: Role,
        department_id=None,
        email: str | None = None,
        dang_hoat_dong: bool = True,
    ) -> User:
        email = email or f"{role.value.lower()}{len(self.user_repo._users)}@congty.vn"
        user = User.create(
            email=Email(email),
            password_hash=PasswordHash(self.hasher.hash("MatKhau123")),
            full_name="Nguyễn Văn A",
            role=role,
            department_id=department_id,
            now=BAY_GIO,
        )
        if not dang_hoat_dong:
            user.deactivate(is_last_active_admin=False, now=BAY_GIO)
        self.user_repo._users[user.id] = user
        return user

    def tao(self) -> CreateUser:
        return CreateUser(
            self.user_repo, self.department_repo, self.audit_repo, self.hasher, self.clock
        )

    def sua(self) -> UpdateUser:
        return UpdateUser(self.user_repo, self.audit_repo, self.clock)

    def vo_hieu_hoa(self) -> DeactivateUser:
        return DeactivateUser(
            self.user_repo, self.token_repo, self.audit_repo, self.clock
        )

    def kich_hoat_lai(self) -> ReactivateUser:
        return ReactivateUser(
            self.user_repo, self.department_repo, self.audit_repo, self.clock
        )

    def doi_vai_tro(self) -> ChangeUserRole:
        return ChangeUserRole(
            self.user_repo, self.department_repo, self.audit_repo, self.clock
        )

    def chuyen_phong(self) -> AssignUserToDepartment:
        return AssignUserToDepartment(
            self.user_repo, self.department_repo, self.audit_repo, self.clock
        )

    def dat_lai_mat_khau(self) -> ResetUserPassword:
        return ResetUserPassword(
            self.user_repo, self.token_repo, self.audit_repo, self.hasher, self.clock
        )

    def danh_sach(self) -> ListUsers:
        return ListUsers(self.user_repo)

    def xem(self) -> GetUser:
        return GetUser(self.user_repo)


class TestTaoNguoiDung:
    async def test_admin_tao_duoc_nhan_vien(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        moi = await bc.tao().execute(
            requester=admin,
            email="moi@congty.vn",
            full_name="Trần Thị B",
            role=Role.STAFF,
            department_id=bc.phong_a.id,
            password="MatKhauTam123",
        )

        assert moi.email == Email("moi@congty.vn")
        assert moi.role is Role.STAFF
        assert moi.department_id == bc.phong_a.id

    async def test_nguoi_dung_moi_buoc_phai_doi_mat_khau(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        moi = await bc.tao().execute(
            requester=admin,
            email="moi@congty.vn",
            full_name="Trần Thị B",
            role=Role.STAFF,
            department_id=bc.phong_a.id,
            password="MatKhauTam123",
        )

        assert moi.must_change_password is True

    async def test_mat_khau_duoc_bam_khong_luu_dang_tho(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        moi = await bc.tao().execute(
            requester=admin,
            email="moi@congty.vn",
            full_name="Trần Thị B",
            role=Role.STAFF,
            department_id=bc.phong_a.id,
            password="MatKhauTam123",
        )

        assert moi.password_hash.value != "MatKhauTam123"
        assert bc.hasher.verify("MatKhauTam123", moi.password_hash.value)

    async def test_manager_khong_tao_duoc_nguoi_dung(self) -> None:
        bc = _BoiCanh()
        manager = bc.them(Role.MANAGER, bc.phong_a.id)

        with pytest.raises(PermissionDeniedError):
            await bc.tao().execute(
                requester=manager,
                email="moi@congty.vn",
                full_name="Trần Thị B",
                role=Role.STAFF,
                department_id=bc.phong_a.id,
                password="MatKhauTam123",
            )

    async def test_staff_khong_tao_duoc_nguoi_dung(self) -> None:
        bc = _BoiCanh()
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        with pytest.raises(PermissionDeniedError):
            await bc.tao().execute(
                requester=staff,
                email="moi@congty.vn",
                full_name="Trần Thị B",
                role=Role.STAFF,
                department_id=bc.phong_a.id,
                password="MatKhauTam123",
            )

    async def test_email_trung_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        bc.them(Role.STAFF, bc.phong_a.id, email="trung@congty.vn")

        with pytest.raises(EmailAlreadyExistsError):
            await bc.tao().execute(
                requester=admin,
                email="TRUNG@congty.vn",
                full_name="Trần Thị B",
                role=Role.STAFF,
                department_id=bc.phong_a.id,
                password="MatKhauTam123",
            )

    async def test_phong_ban_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        with pytest.raises(NotFoundError):
            await bc.tao().execute(
                requester=admin,
                email="moi@congty.vn",
                full_name="Trần Thị B",
                role=Role.STAFF,
                department_id=new_id(),
                password="MatKhauTam123",
            )

    async def test_khong_tao_duoc_manager_thu_hai_trong_phong(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        bc.them(Role.MANAGER, bc.phong_a.id)

        with pytest.raises(DepartmentAlreadyHasManagerError):
            await bc.tao().execute(
                requester=admin,
                email="m2@congty.vn",
                full_name="Trần Thị B",
                role=Role.MANAGER,
                department_id=bc.phong_a.id,
                password="MatKhauTam123",
            )

    async def test_ghi_nhat_ky_khi_tao(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        moi = await bc.tao().execute(
            requester=admin,
            email="moi@congty.vn",
            full_name="Trần Thị B",
            role=Role.STAFF,
            department_id=bc.phong_a.id,
            password="MatKhauTam123",
        )

        ban_ghi = bc.audit_repo.entries[-1]
        assert ban_ghi.action is AuditAction.USER_CREATED
        assert ban_ghi.actor_id == admin.id
        assert ban_ghi.resource_id == str(moi.id)

    async def test_nhat_ky_khong_luu_mat_khau(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        await bc.tao().execute(
            requester=admin,
            email="moi@congty.vn",
            full_name="Trần Thị B",
            role=Role.STAFF,
            department_id=bc.phong_a.id,
            password="MatKhauBiLo999",
        )

        assert "MatKhauBiLo999" not in str(bc.audit_repo.entries[-1].changes)


class TestSuaThongTin:
    async def test_admin_sua_duoc_moi_nguoi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        ket_qua = await bc.sua().execute(
            requester=admin, user_id=staff.id, full_name="Tên Mới"
        )

        assert ket_qua.full_name == "Tên Mới"

    async def test_manager_sua_duoc_staff_phong_minh(self) -> None:
        bc = _BoiCanh()
        manager = bc.them(Role.MANAGER, bc.phong_a.id)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        ket_qua = await bc.sua().execute(
            requester=manager, user_id=staff.id, phone="0912345678"
        )

        assert ket_qua.phone == "0912345678"

    async def test_manager_khong_sua_duoc_staff_phong_khac(self) -> None:
        bc = _BoiCanh()
        manager = bc.them(Role.MANAGER, bc.phong_a.id)
        staff_khac = bc.them(Role.STAFF, bc.phong_b.id)

        with pytest.raises(PermissionDeniedError):
            await bc.sua().execute(
                requester=manager, user_id=staff_khac.id, full_name="Tên Mới"
            )

    async def test_staff_sua_duoc_thong_tin_cua_chinh_minh(self) -> None:
        bc = _BoiCanh()
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        ket_qua = await bc.sua().execute(
            requester=staff, user_id=staff.id, full_name="Tên Tự Đổi"
        )

        assert ket_qua.full_name == "Tên Tự Đổi"

    async def test_staff_khong_sua_duoc_nguoi_khac(self) -> None:
        bc = _BoiCanh()
        staff = bc.them(Role.STAFF, bc.phong_a.id)
        khac = bc.them(Role.STAFF, bc.phong_a.id)

        with pytest.raises(PermissionDeniedError):
            await bc.sua().execute(
                requester=staff, user_id=khac.id, full_name="Tên Mới"
            )

    async def test_khong_tim_thay_nguoi_dung(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        with pytest.raises(NotFoundError):
            await bc.sua().execute(
                requester=admin, user_id=new_id(), full_name="Tên Mới"
            )


class TestVoHieuHoaVaKichHoatLai:
    async def test_admin_vo_hieu_hoa_duoc_nhan_vien(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        ket_qua = await bc.vo_hieu_hoa().execute(requester=admin, user_id=staff.id)

        assert ket_qua.is_active is False

    async def test_vo_hieu_hoa_thu_hoi_moi_refresh_token(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id)
        from src.modules.identity.domain.entities.refresh_token import RefreshToken

        token = RefreshToken.issue(staff.id, "hash_x", BAY_GIO, BAY_GIO)
        await bc.token_repo.add(token)

        await bc.vo_hieu_hoa().execute(requester=admin, user_id=staff.id)

        assert token.is_revoked() is True

    async def test_khong_vo_hieu_hoa_duoc_admin_cuoi_cung(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        with pytest.raises(LastAdminCannotBeDeactivatedError):
            await bc.vo_hieu_hoa().execute(requester=admin, user_id=admin.id)

    async def test_manager_khong_vo_hieu_hoa_duoc_ai(self) -> None:
        bc = _BoiCanh()
        manager = bc.them(Role.MANAGER, bc.phong_a.id)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        with pytest.raises(PermissionDeniedError):
            await bc.vo_hieu_hoa().execute(requester=manager, user_id=staff.id)

    async def test_kich_hoat_lai_nhan_vien(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id, dang_hoat_dong=False)

        ket_qua = await bc.kich_hoat_lai().execute(requester=admin, user_id=staff.id)

        assert ket_qua.is_active is True

    async def test_khong_kich_hoat_lai_duoc_khi_phong_ban_da_dong(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id, dang_hoat_dong=False)
        bc.phong_a.deactivate(active_member_count=0, now=BAY_GIO)

        with pytest.raises(InactiveDepartmentError):
            await bc.kich_hoat_lai().execute(requester=admin, user_id=staff.id)

    async def test_manager_khong_kich_hoat_lai_duoc(self) -> None:
        bc = _BoiCanh()
        manager = bc.them(Role.MANAGER, bc.phong_a.id)
        staff = bc.them(Role.STAFF, bc.phong_a.id, dang_hoat_dong=False)

        with pytest.raises(PermissionDeniedError):
            await bc.kich_hoat_lai().execute(requester=manager, user_id=staff.id)

    async def test_vo_hieu_hoa_nguoi_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        with pytest.raises(NotFoundError):
            await bc.vo_hieu_hoa().execute(requester=admin, user_id=new_id())

    async def test_kich_hoat_lai_nguoi_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        with pytest.raises(NotFoundError):
            await bc.kich_hoat_lai().execute(requester=admin, user_id=new_id())


class TestDoiVaiTroVaChuyenPhong:
    async def test_admin_nang_staff_len_manager(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        ket_qua = await bc.doi_vai_tro().execute(
            requester=admin,
            user_id=staff.id,
            new_role=Role.MANAGER,
            department_id=bc.phong_a.id,
        )

        assert ket_qua.role is Role.MANAGER

    async def test_khong_nang_duoc_khi_phong_da_co_manager(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        bc.them(Role.MANAGER, bc.phong_a.id)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        with pytest.raises(DepartmentAlreadyHasManagerError):
            await bc.doi_vai_tro().execute(
                requester=admin,
                user_id=staff.id,
                new_role=Role.MANAGER,
                department_id=bc.phong_a.id,
            )

    async def test_ha_manager_xuong_staff_duoc(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        manager = bc.them(Role.MANAGER, bc.phong_a.id)

        ket_qua = await bc.doi_vai_tro().execute(
            requester=admin,
            user_id=manager.id,
            new_role=Role.STAFF,
            department_id=bc.phong_a.id,
        )

        assert ket_qua.role is Role.STAFF

    async def test_manager_khong_doi_duoc_vai_tro_cua_ai(self) -> None:
        bc = _BoiCanh()
        manager = bc.them(Role.MANAGER, bc.phong_a.id)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        with pytest.raises(PermissionDeniedError):
            await bc.doi_vai_tro().execute(
                requester=manager,
                user_id=staff.id,
                new_role=Role.MANAGER,
                department_id=bc.phong_a.id,
            )

    async def test_chuyen_nhan_vien_sang_phong_khac(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        ket_qua = await bc.chuyen_phong().execute(
            requester=admin, user_id=staff.id, department_id=bc.phong_b.id
        )

        assert ket_qua.department_id == bc.phong_b.id

    async def test_ghi_nhat_ky_khi_doi_vai_tro(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        await bc.doi_vai_tro().execute(
            requester=admin,
            user_id=staff.id,
            new_role=Role.MANAGER,
            department_id=bc.phong_a.id,
        )

        ban_ghi = bc.audit_repo.entries[-1]
        assert ban_ghi.action is AuditAction.USER_ROLE_CHANGED
        assert ban_ghi.changes is not None
        assert ban_ghi.changes["role"]["truoc"] == "STAFF"
        assert ban_ghi.changes["role"]["sau"] == "MANAGER"

    async def test_doi_vai_tro_sang_phong_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        with pytest.raises(NotFoundError):
            await bc.doi_vai_tro().execute(
                requester=admin,
                user_id=staff.id,
                new_role=Role.MANAGER,
                department_id=new_id(),
            )

    async def test_manager_khong_chuyen_duoc_phong(self) -> None:
        bc = _BoiCanh()
        manager = bc.them(Role.MANAGER, bc.phong_a.id)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        with pytest.raises(PermissionDeniedError):
            await bc.chuyen_phong().execute(
                requester=manager, user_id=staff.id, department_id=bc.phong_b.id
            )

    async def test_chuyen_sang_phong_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        with pytest.raises(NotFoundError):
            await bc.chuyen_phong().execute(
                requester=admin, user_id=staff.id, department_id=new_id()
            )

    async def test_doi_vai_tro_nguoi_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        with pytest.raises(NotFoundError):
            await bc.doi_vai_tro().execute(
                requester=admin,
                user_id=new_id(),
                new_role=Role.MANAGER,
                department_id=bc.phong_a.id,
            )

    async def test_chuyen_phong_nguoi_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        with pytest.raises(NotFoundError):
            await bc.chuyen_phong().execute(
                requester=admin, user_id=new_id(), department_id=bc.phong_a.id
            )


class TestDatLaiMatKhau:
    async def test_admin_dat_lai_mat_khau_cho_nhan_vien(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        await bc.dat_lai_mat_khau().execute(
            requester=admin, user_id=staff.id, new_password="MatKhauTam456"
        )

        assert bc.hasher.verify("MatKhauTam456", staff.password_hash.value)

    async def test_dat_lai_mat_khau_bat_buoc_doi_khi_dang_nhap(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        await bc.dat_lai_mat_khau().execute(
            requester=admin, user_id=staff.id, new_password="MatKhauTam456"
        )

        assert staff.must_change_password is True

    async def test_dat_lai_mat_khau_thu_hoi_moi_phien(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        staff = bc.them(Role.STAFF, bc.phong_a.id)
        from src.modules.identity.domain.entities.refresh_token import RefreshToken

        token = RefreshToken.issue(staff.id, "hash_y", BAY_GIO, BAY_GIO)
        await bc.token_repo.add(token)

        await bc.dat_lai_mat_khau().execute(
            requester=admin, user_id=staff.id, new_password="MatKhauTam456"
        )

        assert token.is_revoked() is True

    async def test_manager_khong_dat_lai_duoc_mat_khau(self) -> None:
        bc = _BoiCanh()
        manager = bc.them(Role.MANAGER, bc.phong_a.id)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        with pytest.raises(PermissionDeniedError):
            await bc.dat_lai_mat_khau().execute(
                requester=manager, user_id=staff.id, new_password="MatKhauTam456"
            )

    async def test_dat_lai_mat_khau_nguoi_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        with pytest.raises(NotFoundError):
            await bc.dat_lai_mat_khau().execute(
                requester=admin, user_id=new_id(), new_password="MatKhauTam456"
            )


class TestDanhSachVaXem:
    async def test_admin_thay_moi_nguoi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        bc.them(Role.STAFF, bc.phong_a.id)
        bc.them(Role.STAFF, bc.phong_b.id)

        trang = await bc.danh_sach().execute(requester=admin)

        assert trang.total == 3

    async def test_manager_chi_thay_phong_minh(self) -> None:
        bc = _BoiCanh()
        manager = bc.them(Role.MANAGER, bc.phong_a.id)
        bc.them(Role.STAFF, bc.phong_a.id)
        bc.them(Role.STAFF, bc.phong_b.id)

        trang = await bc.danh_sach().execute(requester=manager)

        assert trang.total == 2
        assert all(u.department_id == bc.phong_a.id for u in trang.items)

    async def test_manager_yeu_cau_phong_khac_van_chi_thay_phong_minh(self) -> None:
        """Manager truyền department_id của phòng khác không được vượt rào."""
        bc = _BoiCanh()
        manager = bc.them(Role.MANAGER, bc.phong_a.id)
        bc.them(Role.STAFF, bc.phong_b.id)

        trang = await bc.danh_sach().execute(
            requester=manager, department_id=bc.phong_b.id
        )

        assert all(u.department_id == bc.phong_a.id for u in trang.items)

    async def test_staff_khong_xem_duoc_danh_sach(self) -> None:
        bc = _BoiCanh()
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        with pytest.raises(PermissionDeniedError):
            await bc.danh_sach().execute(requester=staff)

    async def test_phan_trang_tra_ve_tong_so_dung(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)
        for _ in range(5):
            bc.them(Role.STAFF, bc.phong_a.id)

        trang = await bc.danh_sach().execute(requester=admin, limit=2, offset=0)

        assert len(trang.items) == 2
        assert trang.total == 6
        assert trang.limit == 2
        assert trang.offset == 0

    async def test_staff_xem_duoc_ho_so_cua_chinh_minh(self) -> None:
        bc = _BoiCanh()
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        ket_qua = await bc.xem().execute(requester=staff, user_id=staff.id)

        assert ket_qua.id == staff.id

    async def test_staff_khong_xem_duoc_nguoi_khac(self) -> None:
        bc = _BoiCanh()
        staff = bc.them(Role.STAFF, bc.phong_a.id)
        khac = bc.them(Role.STAFF, bc.phong_a.id)

        with pytest.raises(PermissionDeniedError):
            await bc.xem().execute(requester=staff, user_id=khac.id)

    async def test_manager_xem_duoc_staff_phong_minh(self) -> None:
        bc = _BoiCanh()
        manager = bc.them(Role.MANAGER, bc.phong_a.id)
        staff = bc.them(Role.STAFF, bc.phong_a.id)

        ket_qua = await bc.xem().execute(requester=manager, user_id=staff.id)

        assert ket_qua.id == staff.id

    async def test_xem_nguoi_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them(Role.ADMIN)

        with pytest.raises(NotFoundError):
            await bc.xem().execute(requester=admin, user_id=new_id())
