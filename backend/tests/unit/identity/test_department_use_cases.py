from datetime import UTC, datetime

import pytest

from src.modules.identity.application.use_cases.create_department import (
    CreateDepartment,
    DepartmentNameAlreadyExistsError,
)
from src.modules.identity.application.use_cases.deactivate_department import (
    DeactivateDepartment,
)
from src.modules.identity.application.use_cases.get_department import GetDepartment
from src.modules.identity.application.use_cases.list_audit_logs import ListAuditLogs
from src.modules.identity.application.use_cases.list_departments import ListDepartments
from src.modules.identity.application.use_cases.update_department import (
    UpdateDepartment,
)
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.department import (
    Department,
    DepartmentHasActiveMembersError,
)
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.identity.fakes import (
    FakeAuditLogRepository,
    FakeClock,
    FakeDepartmentRepository,
    FakeUserRepository,
)

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


class _BoiCanh:
    def __init__(self) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.department_repo = FakeDepartmentRepository()
        self.user_repo = FakeUserRepository()
        self.audit_repo = FakeAuditLogRepository()

    def them_user(self, role: Role, department_id=None) -> User:
        user = User.create(
            email=Email(f"{role.value.lower()}{len(self.user_repo._users)}@congty.vn"),
            password_hash=PasswordHash("$2b$12$hash"),
            full_name="Người dùng",
            role=role,
            department_id=department_id,
            now=BAY_GIO,
        )
        self.user_repo._users[user.id] = user
        return user

    def them_phong(self, ten: str) -> Department:
        phong = Department.create(ten, None, BAY_GIO)
        self.department_repo._departments[phong.id] = phong
        return phong

    def tao(self) -> CreateDepartment:
        return CreateDepartment(self.department_repo, self.audit_repo, self.clock)

    def sua(self) -> UpdateDepartment:
        return UpdateDepartment(self.department_repo, self.audit_repo, self.clock)

    def dong(self) -> DeactivateDepartment:
        return DeactivateDepartment(
            self.department_repo, self.user_repo, self.audit_repo, self.clock
        )

    def danh_sach(self) -> ListDepartments:
        return ListDepartments(self.department_repo)

    def xem(self) -> GetDepartment:
        return GetDepartment(self.department_repo)

    def nhat_ky(self) -> ListAuditLogs:
        return ListAuditLogs(self.audit_repo)


class TestTaoPhongBan:
    async def test_admin_tao_duoc_phong_ban(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)

        phong = await bc.tao().execute(requester=admin, name="Kinh doanh")

        assert phong.name == "Kinh doanh"
        assert phong.is_active is True

    async def test_ten_trung_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)
        bc.them_phong("Kinh doanh")

        with pytest.raises(DepartmentNameAlreadyExistsError):
            await bc.tao().execute(requester=admin, name="kinh doanh")

    async def test_manager_khong_tao_duoc_phong_ban(self) -> None:
        bc = _BoiCanh()
        phong = bc.them_phong("Phòng A")
        manager = bc.them_user(Role.MANAGER, phong.id)

        with pytest.raises(PermissionDeniedError):
            await bc.tao().execute(requester=manager, name="Phòng mới")

    async def test_ghi_nhat_ky_khi_tao(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)

        phong = await bc.tao().execute(requester=admin, name="Kinh doanh")

        ban_ghi = bc.audit_repo.entries[-1]
        assert ban_ghi.action is AuditAction.DEPARTMENT_CREATED
        assert ban_ghi.resource_id == str(phong.id)


class TestSuaPhongBan:
    async def test_doi_ten_phong_ban(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)
        phong = bc.them_phong("Tên Cũ")

        ket_qua = await bc.sua().execute(
            requester=admin, department_id=phong.id, name="Tên Mới"
        )

        assert ket_qua.name == "Tên Mới"

    async def test_doi_sang_ten_da_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)
        bc.them_phong("Đã Có")
        phong = bc.them_phong("Phòng B")

        with pytest.raises(DepartmentNameAlreadyExistsError):
            await bc.sua().execute(
                requester=admin, department_id=phong.id, name="Đã Có"
            )

    async def test_giu_nguyen_ten_cua_chinh_no_thi_khong_bao_trung(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)
        phong = bc.them_phong("Giữ Nguyên")

        ket_qua = await bc.sua().execute(
            requester=admin,
            department_id=phong.id,
            name="Giữ Nguyên",
            description="Mô tả mới",
        )

        assert ket_qua.description == "Mô tả mới"

    async def test_manager_khong_sua_duoc_phong_ban(self) -> None:
        bc = _BoiCanh()
        phong = bc.them_phong("Phòng A")
        manager = bc.them_user(Role.MANAGER, phong.id)

        with pytest.raises(PermissionDeniedError):
            await bc.sua().execute(
                requester=manager, department_id=phong.id, name="Tên Mới"
            )

    async def test_sua_phong_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)

        with pytest.raises(NotFoundError):
            await bc.sua().execute(
                requester=admin, department_id=new_id(), name="Tên Mới"
            )


class TestDongPhongBan:
    async def test_dong_duoc_khi_khong_con_nhan_vien(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)
        phong = bc.them_phong("Phòng Trống")

        ket_qua = await bc.dong().execute(requester=admin, department_id=phong.id)

        assert ket_qua.is_active is False

    async def test_khong_dong_duoc_khi_con_nhan_vien(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)
        phong = bc.them_phong("Phòng Đông")
        bc.them_user(Role.STAFF, phong.id)

        with pytest.raises(DepartmentHasActiveMembersError):
            await bc.dong().execute(requester=admin, department_id=phong.id)

    async def test_khong_tim_thay_phong_ban(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)

        with pytest.raises(NotFoundError):
            await bc.dong().execute(requester=admin, department_id=new_id())

    async def test_manager_khong_dong_duoc_phong_ban(self) -> None:
        bc = _BoiCanh()
        phong = bc.them_phong("Phòng A")
        manager = bc.them_user(Role.MANAGER, phong.id)

        with pytest.raises(PermissionDeniedError):
            await bc.dong().execute(requester=manager, department_id=phong.id)


class TestDanhSachPhongBan:
    async def test_moi_nguoi_dang_nhap_deu_xem_duoc(self) -> None:
        """Staff cần biết tên phòng ban để hiển thị trên giao diện."""
        bc = _BoiCanh()
        phong = bc.them_phong("Phòng A")
        staff = bc.them_user(Role.STAFF, phong.id)

        trang = await bc.danh_sach().execute(requester=staff)

        assert trang.total == 1

    async def test_loc_theo_trang_thai(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)
        bc.them_phong("Đang Mở")
        da_dong = bc.them_phong("Đã Đóng")
        da_dong.deactivate(active_member_count=0, now=BAY_GIO)

        trang = await bc.danh_sach().execute(requester=admin, is_active=True)

        assert trang.total == 1
        assert trang.items[0].name == "Đang Mở"

    async def test_xem_chi_tiet_phong_ban(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)
        phong = bc.them_phong("Phòng A")

        ket_qua = await bc.xem().execute(requester=admin, department_id=phong.id)

        assert ket_qua.id == phong.id

    async def test_xem_phong_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)

        with pytest.raises(NotFoundError):
            await bc.xem().execute(requester=admin, department_id=new_id())


class TestNhatKy:
    async def test_admin_xem_duoc_nhat_ky(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)
        await bc.audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_CREATED,
                actor_id=admin.id,
                resource_type="user",
                resource_id="x",
                now=BAY_GIO,
            )
        )

        trang = await bc.nhat_ky().execute(requester=admin)

        assert trang.total == 1

    async def test_manager_khong_xem_duoc_nhat_ky(self) -> None:
        bc = _BoiCanh()
        phong = bc.them_phong("Phòng A")
        manager = bc.them_user(Role.MANAGER, phong.id)

        with pytest.raises(PermissionDeniedError):
            await bc.nhat_ky().execute(requester=manager)

    async def test_staff_khong_xem_duoc_nhat_ky(self) -> None:
        bc = _BoiCanh()
        phong = bc.them_phong("Phòng A")
        staff = bc.them_user(Role.STAFF, phong.id)

        with pytest.raises(PermissionDeniedError):
            await bc.nhat_ky().execute(requester=staff)

    async def test_loc_nhat_ky_theo_hanh_dong(self) -> None:
        bc = _BoiCanh()
        admin = bc.them_user(Role.ADMIN)
        for hanh_dong in (AuditAction.USER_CREATED, AuditAction.USER_DEACTIVATED):
            await bc.audit_repo.add(
                AuditLog.record(
                    action=hanh_dong,
                    actor_id=admin.id,
                    resource_type="user",
                    resource_id="x",
                    now=BAY_GIO,
                )
            )

        trang = await bc.nhat_ky().execute(
            requester=admin, action=AuditAction.USER_CREATED
        )

        assert trang.total == 1
