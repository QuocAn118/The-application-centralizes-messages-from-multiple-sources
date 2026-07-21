# OmniChat Foundation — Phần 4b: Use case quản trị (Task 14–15)

> Tiếp nối [phần 4](2026-07-21-omnichat-foundation-part4-api.md). Global Constraints ở [phần 1](2026-07-21-omnichat-foundation.md) áp dụng cho mọi task tại đây.

---

## Task 14: Use case quản lý người dùng

**Files:**
- Create: `backend/src/modules/identity/application/dto/user_dto.py`
- Create: `backend/src/modules/identity/application/use_cases/create_user.py`
- Create: `backend/src/modules/identity/application/use_cases/update_user.py`
- Create: `backend/src/modules/identity/application/use_cases/deactivate_user.py`
- Create: `backend/src/modules/identity/application/use_cases/reactivate_user.py`
- Create: `backend/src/modules/identity/application/use_cases/change_user_role.py`
- Create: `backend/src/modules/identity/application/use_cases/assign_user_to_department.py`
- Create: `backend/src/modules/identity/application/use_cases/reset_user_password.py`
- Create: `backend/src/modules/identity/application/use_cases/list_users.py`
- Create: `backend/src/modules/identity/application/use_cases/get_user.py`
- Test: `backend/tests/unit/identity/test_user_use_cases.py`

**Interfaces:**
- Consumes: repository interface (Task 8), `IPasswordHasher` (Task 12), entity `User` (Task 6).
- Produces:
  - `Page[T]` — frozen dataclass generic: `items: list[T]`, `total: int`, `limit: int`, `offset: int`.
  - `CreateUser(user_repo, department_repo, audit_repo, hasher, clock)` — `execute(requester, email, full_name, role, department_id, password, phone=None) -> User`.
  - `UpdateUser(user_repo, audit_repo, clock)` — `execute(requester, user_id, full_name=None, phone=None) -> User`.
  - `DeactivateUser(user_repo, refresh_token_repo, audit_repo, clock)` — `execute(requester, user_id) -> User`.
  - `ReactivateUser(user_repo, department_repo, audit_repo, clock)` — `execute(requester, user_id) -> User`.
  - `ChangeUserRole(user_repo, department_repo, audit_repo, clock)` — `execute(requester, user_id, new_role, department_id) -> User`.
  - `AssignUserToDepartment(user_repo, department_repo, audit_repo, clock)` — `execute(requester, user_id, department_id) -> User`.
  - `ResetUserPassword(user_repo, refresh_token_repo, audit_repo, hasher, clock)` — `execute(requester, user_id, new_password) -> None`.
  - `ListUsers(user_repo)` — `execute(requester, department_id=None, role=None, is_active=None, search=None, limit=50, offset=0) -> Page[User]`.
  - `GetUser(user_repo)` — `execute(requester, user_id) -> User`.
  - `EmailAlreadyExistsError` — kế thừa `ConflictError`.

**Quy tắc phân quyền của các use case này:**

| Use case | Admin | Manager | Staff |
|---|---|---|---|
| `CreateUser` | ✓ | ✗ | ✗ |
| `UpdateUser` | mọi người | Staff phòng mình + chính mình | chỉ chính mình |
| `DeactivateUser` / `ReactivateUser` | ✓ | ✗ | ✗ |
| `ChangeUserRole` / `AssignUserToDepartment` | ✓ | ✗ | ✗ |
| `ResetUserPassword` | ✓ | ✗ | ✗ |
| `ListUsers` | tất cả | chỉ phòng mình | ✗ |
| `GetUser` | mọi người | phòng mình + chính mình | chỉ chính mình |

- [ ] **Step 1: Viết `dto/user_dto.py`**

```python
"""DTO dùng chung cho các use case quản lý."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Page[T]:
    """Một trang kết quả kèm tổng số bản ghi.

    ``total`` là tổng số bản ghi khớp bộ lọc, không phải số phần tử trong
    ``items`` — client cần nó để dựng thanh phân trang.
    """

    items: list[T]
    total: int
    limit: int
    offset: int
```

- [ ] **Step 2: Viết test cho nhóm use case người dùng**

File `backend/tests/unit/identity/test_user_use_cases.py`:

```python
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

        with pytest.raises(Exception):
            await bc.kich_hoat_lai().execute(requester=admin, user_id=staff.id)


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
```

- [ ] **Step 3: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/unit/identity/test_user_use_cases.py -v
```

Expected: FAIL với `ModuleNotFoundError` cho `create_user`.

- [ ] **Step 4: Viết `create_user.py`**

```python
"""Use case tạo người dùng."""

from uuid import UUID

from src.modules.identity.application.ports import IPasswordHasher
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import (
    DepartmentAlreadyHasManagerError,
    User,
)
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.shared.application.ports import IClock


class EmailAlreadyExistsError(ConflictError):
    """Email đã được dùng cho một tài khoản khác."""

    def __init__(self, email: str) -> None:
        super().__init__(
            f"Email {email} đã được sử dụng.", code="EMAIL_ALREADY_EXISTS"
        )


class CreateUser:
    """Tạo tài khoản mới. Chỉ quản trị viên được phép."""

    def __init__(
        self,
        user_repo: IUserRepository,
        department_repo: IDepartmentRepository,
        audit_repo: IAuditLogRepository,
        hasher: IPasswordHasher,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._department_repo = department_repo
        self._audit_repo = audit_repo
        self._hasher = hasher
        self._clock = clock

    async def execute(
        self,
        requester: User,
        email: str,
        full_name: str,
        role: Role,
        department_id: UUID | None,
        password: str,
        phone: str | None = None,
    ) -> User:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được tạo tài khoản.", code="ADMIN_REQUIRED"
            )

        dia_chi = Email(email)
        if await self._user_repo.get_by_email(dia_chi) is not None:
            raise EmailAlreadyExistsError(dia_chi.value)

        if department_id is not None:
            phong = await self._department_repo.get_by_id(department_id)
            if phong is None or not phong.is_active:
                raise NotFoundError(
                    "Không tìm thấy phòng ban đang hoạt động.",
                    code="DEPARTMENT_NOT_FOUND",
                )

        if role is Role.MANAGER and department_id is not None:
            if await self._user_repo.has_active_manager(department_id):
                raise DepartmentAlreadyHasManagerError

        bay_gio = self._clock.now()
        user = User.create(
            email=dia_chi,
            password_hash=PasswordHash(self._hasher.hash(password)),
            full_name=full_name,
            role=role,
            department_id=department_id,
            now=bay_gio,
            phone=phone,
            must_change_password=True,
        )
        await self._user_repo.add(user)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_CREATED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
                changes={
                    "email": user.email.value,
                    "role": user.role.value,
                    "department_id": str(department_id) if department_id else None,
                },
            )
        )
        return user
```

- [ ] **Step 5: Viết `update_user.py`**

```python
"""Use case cập nhật thông tin hồ sơ."""

from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class UpdateUser:
    """Sửa họ tên và số điện thoại.

    Không đụng tới email, vai trò hay phòng ban — mỗi thứ đó có use case riêng
    vì chúng mang quy tắc nghiệp vụ khác nhau.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(
        self,
        requester: User,
        user_id: UUID,
        full_name: str | None = None,
        phone: str | None = None,
    ) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(
                "Không tìm thấy người dùng.", code="USER_NOT_FOUND"
            )

        la_chinh_minh = requester.id == user.id
        if not la_chinh_minh and not requester.can_manage(user):
            raise PermissionDeniedError(
                "Bạn không có quyền sửa thông tin người dùng này.",
                code="CANNOT_MANAGE_USER",
            )

        bay_gio = self._clock.now()
        truoc = {"full_name": user.full_name, "phone": user.phone}
        user.update_profile(full_name=full_name, phone=phone, now=bay_gio)
        await self._user_repo.update(user)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_UPDATED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
                changes={
                    "truoc": truoc,
                    "sau": {"full_name": user.full_name, "phone": user.phone},
                },
            )
        )
        return user
```

- [ ] **Step 6: Viết `deactivate_user.py` và `reactivate_user.py`**

File `deactivate_user.py`:

```python
"""Use case vô hiệu hoá người dùng."""

from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.refresh_token_repository import (
    IRefreshTokenRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class DeactivateUser:
    """Vô hiệu hoá tài khoản và thu hồi mọi phiên đăng nhập.

    Access token đang lưu hành vẫn dùng được tới khi hết hạn — giới hạn đã
    biết, xem mục 9 của spec.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        refresh_token_repo: IRefreshTokenRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(self, requester: User, user_id: UUID) -> User:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được vô hiệu hoá tài khoản.",
                code="ADMIN_REQUIRED",
            )

        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy người dùng.", code="USER_NOT_FOUND")

        so_admin = await self._user_repo.count_active_admins()
        la_admin_cuoi = user.role is Role.ADMIN and user.is_active and so_admin <= 1

        bay_gio = self._clock.now()
        user.deactivate(is_last_active_admin=la_admin_cuoi, now=bay_gio)
        await self._user_repo.update(user)
        await self._refresh_token_repo.revoke_all_for_user(user.id, now=bay_gio)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_DEACTIVATED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
            )
        )
        return user
```

File `reactivate_user.py`:

```python
"""Use case kích hoạt lại người dùng."""

from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class ReactivateUser:
    """Kích hoạt lại tài khoản đã bị vô hiệu hoá."""

    def __init__(
        self,
        user_repo: IUserRepository,
        department_repo: IDepartmentRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._department_repo = department_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(self, requester: User, user_id: UUID) -> User:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được kích hoạt lại tài khoản.",
                code="ADMIN_REQUIRED",
            )

        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy người dùng.", code="USER_NOT_FOUND")

        phong_dang_hoat_dong = True
        phong_da_co_quan_ly = False
        if user.department_id is not None:
            phong = await self._department_repo.get_by_id(user.department_id)
            phong_dang_hoat_dong = phong is not None and phong.is_active
            phong_da_co_quan_ly = await self._user_repo.has_active_manager(
                user.department_id, exclude_user_id=user.id
            )

        bay_gio = self._clock.now()
        user.reactivate(
            department_is_active=phong_dang_hoat_dong,
            department_has_active_manager=phong_da_co_quan_ly,
            now=bay_gio,
        )
        await self._user_repo.update(user)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_REACTIVATED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
            )
        )
        return user
```

- [ ] **Step 7: Viết `change_user_role.py` và `assign_user_to_department.py`**

File `change_user_role.py`:

```python
"""Use case đổi vai trò người dùng."""

from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class ChangeUserRole:
    """Chuyển đổi giữa Nhân viên và Quản lý."""

    def __init__(
        self,
        user_repo: IUserRepository,
        department_repo: IDepartmentRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._department_repo = department_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(
        self,
        requester: User,
        user_id: UUID,
        new_role: Role,
        department_id: UUID | None,
    ) -> User:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được thay đổi vai trò.", code="ADMIN_REQUIRED"
            )

        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy người dùng.", code="USER_NOT_FOUND")

        if department_id is not None:
            phong = await self._department_repo.get_by_id(department_id)
            if phong is None or not phong.is_active:
                raise NotFoundError(
                    "Không tìm thấy phòng ban đang hoạt động.",
                    code="DEPARTMENT_NOT_FOUND",
                )

        da_co_quan_ly = False
        if department_id is not None:
            da_co_quan_ly = await self._user_repo.has_active_manager(
                department_id, exclude_user_id=user.id
            )

        vai_tro_cu = user.role
        bay_gio = self._clock.now()
        user.change_role(
            new_role=new_role,
            department_id=department_id,
            department_has_active_manager=da_co_quan_ly,
            now=bay_gio,
        )
        await self._user_repo.update(user)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_ROLE_CHANGED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
                changes={
                    "role": {"truoc": vai_tro_cu.value, "sau": new_role.value}
                },
            )
        )
        return user
```

File `assign_user_to_department.py`:

```python
"""Use case chuyển người dùng sang phòng ban khác."""

from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class AssignUserToDepartment:
    """Chuyển người dùng sang phòng ban khác, giữ nguyên vai trò."""

    def __init__(
        self,
        user_repo: IUserRepository,
        department_repo: IDepartmentRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._department_repo = department_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(
        self, requester: User, user_id: UUID, department_id: UUID | None
    ) -> User:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được chuyển phòng ban.", code="ADMIN_REQUIRED"
            )

        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy người dùng.", code="USER_NOT_FOUND")

        if department_id is not None:
            phong = await self._department_repo.get_by_id(department_id)
            if phong is None or not phong.is_active:
                raise NotFoundError(
                    "Không tìm thấy phòng ban đang hoạt động.",
                    code="DEPARTMENT_NOT_FOUND",
                )

        da_co_quan_ly = False
        if department_id is not None:
            da_co_quan_ly = await self._user_repo.has_active_manager(
                department_id, exclude_user_id=user.id
            )

        phong_cu = user.department_id
        bay_gio = self._clock.now()
        user.assign_to_department(
            department_id=department_id,
            department_has_active_manager=da_co_quan_ly,
            now=bay_gio,
        )
        await self._user_repo.update(user)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_DEPARTMENT_CHANGED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
                changes={
                    "department_id": {
                        "truoc": str(phong_cu) if phong_cu else None,
                        "sau": str(department_id) if department_id else None,
                    }
                },
            )
        )
        return user
```

- [ ] **Step 8: Viết `reset_user_password.py`**

```python
"""Use case quản trị viên đặt lại mật khẩu cho người dùng."""

from uuid import UUID

from src.modules.identity.application.ports import IPasswordHasher
from src.modules.identity.application.use_cases.change_password import kiem_tra_do_manh
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.refresh_token_repository import (
    IRefreshTokenRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class ResetUserPassword:
    """Quản trị viên cấp mật khẩu tạm cho người dùng.

    Đây là cơ chế khôi phục duy nhất của hệ thống — không có chức năng quên
    mật khẩu qua email.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        refresh_token_repo: IRefreshTokenRepository,
        audit_repo: IAuditLogRepository,
        hasher: IPasswordHasher,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._audit_repo = audit_repo
        self._hasher = hasher
        self._clock = clock

    async def execute(
        self, requester: User, user_id: UUID, new_password: str
    ) -> None:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được đặt lại mật khẩu.", code="ADMIN_REQUIRED"
            )

        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy người dùng.", code="USER_NOT_FOUND")

        kiem_tra_do_manh(new_password)

        bay_gio = self._clock.now()
        user.set_password(
            PasswordHash(self._hasher.hash(new_password)),
            must_change=True,
            now=bay_gio,
        )
        await self._user_repo.update(user)
        await self._refresh_token_repo.revoke_all_for_user(user.id, now=bay_gio)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_PASSWORD_RESET,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
            )
        )
```

- [ ] **Step 9: Viết `list_users.py` và `get_user.py`**

File `list_users.py`:

```python
"""Use case liệt kê người dùng."""

from uuid import UUID

from src.modules.identity.application.dto.user_dto import Page
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import PermissionDeniedError

GIOI_HAN_TOI_DA = 100


class ListUsers:
    """Liệt kê người dùng theo phạm vi quyền của người gọi.

    Quản lý chỉ thấy được phòng ban của mình, kể cả khi họ truyền
    ``department_id`` của phòng khác — bộ lọc bị ghi đè chứ không báo lỗi, để
    không tiết lộ phòng ban nào tồn tại.
    """

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def execute(
        self,
        requester: User,
        department_id: UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[User]:
        if requester.role is Role.STAFF:
            raise PermissionDeniedError(
                "Bạn không có quyền xem danh sách người dùng.",
                code="INSUFFICIENT_ROLE",
            )

        pham_vi = department_id
        if requester.role is Role.MANAGER:
            pham_vi = requester.department_id

        gioi_han = min(max(limit, 1), GIOI_HAN_TOI_DA)
        vi_tri = max(offset, 0)

        items = await self._user_repo.list_users(
            department_id=pham_vi,
            role=role,
            is_active=is_active,
            search=search,
            limit=gioi_han,
            offset=vi_tri,
        )
        tong = await self._user_repo.count_users(
            department_id=pham_vi, role=role, is_active=is_active, search=search
        )
        return Page(items=items, total=tong, limit=gioi_han, offset=vi_tri)
```

File `get_user.py`:

```python
"""Use case xem chi tiết một người dùng."""

from uuid import UUID

from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError


class GetUser:
    """Xem hồ sơ một người dùng."""

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, requester: User, user_id: UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy người dùng.", code="USER_NOT_FOUND")

        if requester.id == user.id:
            return user
        if requester.can_manage(user):
            return user

        raise PermissionDeniedError(
            "Bạn không có quyền xem thông tin người dùng này.",
            code="CANNOT_VIEW_USER",
        )
```

- [ ] **Step 10: Chạy test để xác nhận thành công**

```bash
cd backend
uv run pytest tests/unit/identity/test_user_use_cases.py -v
```

Expected: `36 passed`.

- [ ] **Step 11: Kiểm tra chất lượng mã**

```bash
uv run mypy src
uv run ruff check .
uv run lint-imports
```

Expected: xanh.

- [ ] **Step 12: Commit**

```bash
git add backend/src/modules/identity/application backend/tests/unit/identity/test_user_use_cases.py
git commit -m "feat: add user management use cases with role-scoped permissions"
```

---

## Task 15: Use case phòng ban và nhật ký

**Files:**
- Create: `backend/src/modules/identity/application/use_cases/create_department.py`
- Create: `backend/src/modules/identity/application/use_cases/update_department.py`
- Create: `backend/src/modules/identity/application/use_cases/deactivate_department.py`
- Create: `backend/src/modules/identity/application/use_cases/list_departments.py`
- Create: `backend/src/modules/identity/application/use_cases/get_department.py`
- Create: `backend/src/modules/identity/application/use_cases/list_audit_logs.py`
- Test: `backend/tests/unit/identity/test_department_use_cases.py`

**Interfaces:**
- Consumes: repository interface (Task 8), `Page` (Task 14).
- Produces:
  - `CreateDepartment(department_repo, audit_repo, clock)` — `execute(requester, name, description=None) -> Department`.
  - `UpdateDepartment(department_repo, audit_repo, clock)` — `execute(requester, department_id, name=None, description=None) -> Department`.
  - `DeactivateDepartment(department_repo, user_repo, audit_repo, clock)` — `execute(requester, department_id) -> Department`.
  - `ListDepartments(department_repo)` — `execute(requester, is_active=None, limit=50, offset=0) -> Page[Department]`.
  - `GetDepartment(department_repo)` — `execute(requester, department_id) -> Department`.
  - `ListAuditLogs(audit_repo)` — `execute(requester, actor_id=None, action=None, resource_type=None, from_time=None, to_time=None, limit=50, offset=0) -> Page[AuditLog]`.
  - `DepartmentNameAlreadyExistsError` — kế thừa `ConflictError`.

- [ ] **Step 1: Viết test**

File `backend/tests/unit/identity/test_department_use_cases.py`:

```python
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
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/unit/identity/test_department_use_cases.py -v
```

Expected: FAIL với `ModuleNotFoundError`.

- [ ] **Step 3: Viết `create_department.py`**

```python
"""Use case tạo phòng ban."""

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import ConflictError, PermissionDeniedError
from src.shared.application.ports import IClock


class DepartmentNameAlreadyExistsError(ConflictError):
    """Tên phòng ban đã tồn tại trong các phòng đang hoạt động."""

    def __init__(self, ten: str) -> None:
        super().__init__(
            f"Phòng ban {ten!r} đã tồn tại.", code="DEPARTMENT_NAME_EXISTS"
        )


class CreateDepartment:
    """Tạo phòng ban mới. Chỉ quản trị viên được phép."""

    def __init__(
        self,
        department_repo: IDepartmentRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._department_repo = department_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(
        self, requester: User, name: str, description: str | None = None
    ) -> Department:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được tạo phòng ban.", code="ADMIN_REQUIRED"
            )

        if await self._department_repo.get_by_name(name) is not None:
            raise DepartmentNameAlreadyExistsError(name.strip())

        bay_gio = self._clock.now()
        phong = Department.create(name=name, description=description, now=bay_gio)
        await self._department_repo.add(phong)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.DEPARTMENT_CREATED,
                actor_id=requester.id,
                resource_type="department",
                resource_id=str(phong.id),
                now=bay_gio,
                changes={"name": phong.name},
            )
        )
        return phong
```

- [ ] **Step 4: Viết `update_department.py`**

```python
"""Use case cập nhật phòng ban."""

from uuid import UUID

from src.modules.identity.application.use_cases.create_department import (
    DepartmentNameAlreadyExistsError,
)
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class UpdateDepartment:
    """Sửa tên và mô tả phòng ban."""

    def __init__(
        self,
        department_repo: IDepartmentRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._department_repo = department_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(
        self,
        requester: User,
        department_id: UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> Department:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được sửa phòng ban.", code="ADMIN_REQUIRED"
            )

        phong = await self._department_repo.get_by_id(department_id)
        if phong is None:
            raise NotFoundError(
                "Không tìm thấy phòng ban.", code="DEPARTMENT_NOT_FOUND"
            )

        bay_gio = self._clock.now()
        ten_cu = phong.name

        if name is not None:
            trung = await self._department_repo.get_by_name(name)
            # Đổi tên thành chính tên cũ không phải là trùng lặp.
            if trung is not None and trung.id != phong.id:
                raise DepartmentNameAlreadyExistsError(name.strip())
            phong.rename(name, now=bay_gio)

        if description is not None:
            phong.update_description(description, now=bay_gio)

        await self._department_repo.update(phong)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.DEPARTMENT_UPDATED,
                actor_id=requester.id,
                resource_type="department",
                resource_id=str(phong.id),
                now=bay_gio,
                changes={"name": {"truoc": ten_cu, "sau": phong.name}},
            )
        )
        return phong
```

- [ ] **Step 5: Viết `deactivate_department.py`**

```python
"""Use case vô hiệu hoá phòng ban."""

from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class DeactivateDepartment:
    """Vô hiệu hoá phòng ban.

    Số nhân viên đang hoạt động được đếm ở đây rồi truyền vào entity — domain
    không truy cập repository.
    """

    def __init__(
        self,
        department_repo: IDepartmentRepository,
        user_repo: IUserRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._department_repo = department_repo
        self._user_repo = user_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(self, requester: User, department_id: UUID) -> Department:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được vô hiệu hoá phòng ban.",
                code="ADMIN_REQUIRED",
            )

        phong = await self._department_repo.get_by_id(department_id)
        if phong is None:
            raise NotFoundError(
                "Không tìm thấy phòng ban.", code="DEPARTMENT_NOT_FOUND"
            )

        so_nhan_vien = await self._user_repo.count_active_in_department(department_id)

        bay_gio = self._clock.now()
        phong.deactivate(active_member_count=so_nhan_vien, now=bay_gio)
        await self._department_repo.update(phong)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.DEPARTMENT_DEACTIVATED,
                actor_id=requester.id,
                resource_type="department",
                resource_id=str(phong.id),
                now=bay_gio,
            )
        )
        return phong
```

- [ ] **Step 6: Viết `list_departments.py` và `get_department.py`**

File `list_departments.py`:

```python
"""Use case liệt kê phòng ban."""

from src.modules.identity.application.dto.user_dto import Page
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)

GIOI_HAN_TOI_DA = 100


class ListDepartments:
    """Liệt kê phòng ban.

    Mọi người dùng đã đăng nhập đều xem được: giao diện cần tên phòng ban để
    hiển thị, và danh sách này không chứa thông tin nhạy cảm.
    """

    def __init__(self, department_repo: IDepartmentRepository) -> None:
        self._department_repo = department_repo

    async def execute(
        self,
        requester: User,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[Department]:
        gioi_han = min(max(limit, 1), GIOI_HAN_TOI_DA)
        vi_tri = max(offset, 0)

        items = await self._department_repo.list_departments(
            is_active=is_active, limit=gioi_han, offset=vi_tri
        )
        tong = await self._department_repo.count_departments(is_active=is_active)
        return Page(items=items, total=tong, limit=gioi_han, offset=vi_tri)
```

File `get_department.py`:

```python
"""Use case xem chi tiết phòng ban."""

from uuid import UUID

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)
from src.shared.application.exceptions import NotFoundError


class GetDepartment:
    """Xem chi tiết một phòng ban."""

    def __init__(self, department_repo: IDepartmentRepository) -> None:
        self._department_repo = department_repo

    async def execute(self, requester: User, department_id: UUID) -> Department:
        phong = await self._department_repo.get_by_id(department_id)
        if phong is None:
            raise NotFoundError(
                "Không tìm thấy phòng ban.", code="DEPARTMENT_NOT_FOUND"
            )
        return phong
```

- [ ] **Step 7: Viết `list_audit_logs.py`**

```python
"""Use case tra cứu nhật ký kiểm toán."""

from datetime import datetime
from uuid import UUID

from src.modules.identity.application.dto.user_dto import Page
from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import PermissionDeniedError

GIOI_HAN_TOI_DA = 100


class ListAuditLogs:
    """Tra cứu nhật ký. Chỉ quản trị viên được phép.

    Nhật ký cho thấy toàn bộ hoạt động quản trị của hệ thống nên không mở cho
    quản lý cấp phòng.
    """

    def __init__(self, audit_repo: IAuditLogRepository) -> None:
        self._audit_repo = audit_repo

    async def execute(
        self,
        requester: User,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[AuditLog]:
        if requester.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Chỉ quản trị viên được xem nhật ký hệ thống.",
                code="ADMIN_REQUIRED",
            )

        gioi_han = min(max(limit, 1), GIOI_HAN_TOI_DA)
        vi_tri = max(offset, 0)

        items = await self._audit_repo.list_entries(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            from_time=from_time,
            to_time=to_time,
            limit=gioi_han,
            offset=vi_tri,
        )
        tong = await self._audit_repo.count_entries(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            from_time=from_time,
            to_time=to_time,
        )
        return Page(items=items, total=tong, limit=gioi_han, offset=vi_tri)
```

- [ ] **Step 8: Chạy toàn bộ test unit**

```bash
cd backend
uv run pytest tests/unit -v
```

Expected: toàn bộ xanh.

- [ ] **Step 9: Đo coverage tầng application**

```bash
uv run pytest tests/unit --cov=src/modules/identity/application --cov=src/modules/identity/domain --cov-report=term-missing
```

Expected: ≥ 90%.

- [ ] **Step 10: Kiểm tra chất lượng mã**

```bash
uv run mypy src
uv run ruff check .
uv run lint-imports
```

Expected: xanh.

- [ ] **Step 11: Commit**

```bash
git add backend/src/modules/identity/application backend/tests/unit/identity/test_department_use_cases.py
git commit -m "feat: add department and audit log use cases"
```

---

## Tiếp theo

- [Phần 4c — FastAPI và router](2026-07-21-omnichat-foundation-part4c-http.md) (Task 16–18)
