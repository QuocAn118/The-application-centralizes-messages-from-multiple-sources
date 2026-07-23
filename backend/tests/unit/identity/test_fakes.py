"""Fake cũng cần test — fake sai sẽ làm mọi test dùng nó trở nên vô nghĩa."""

from datetime import UTC, datetime

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.shared.domain.identifiers import new_id
from tests.unit.identity.fakes import (
    FakeDepartmentRepository,
    FakeRefreshTokenRepository,
    FakeUserRepository,
)

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
PHONG_A = new_id()
PHONG_B = new_id()


def _user(role: Role, department_id, email: str, is_active: bool = True) -> User:
    u = User.create(
        email=Email(email),
        password_hash=PasswordHash("$2b$12$x"),
        full_name="Người dùng",
        role=role,
        department_id=department_id,
        now=BAY_GIO,
    )
    if not is_active:
        u.deactivate(is_last_active_admin=False, now=BAY_GIO)
    return u


async def test_tim_duoc_user_theo_email_khong_phan_biet_hoa_thuong() -> None:
    repo = FakeUserRepository([_user(Role.STAFF, PHONG_A, "a@congty.vn")])

    assert await repo.get_by_email(Email("A@CONGTY.VN")) is not None


async def test_dem_dung_nhan_vien_dang_hoat_dong_trong_phong() -> None:
    repo = FakeUserRepository(
        [
            _user(Role.STAFF, PHONG_A, "a@congty.vn"),
            _user(Role.STAFF, PHONG_A, "b@congty.vn", is_active=False),
            _user(Role.STAFF, PHONG_B, "c@congty.vn"),
        ]
    )

    assert await repo.count_active_in_department(PHONG_A) == 1


async def test_has_active_manager_bo_qua_chinh_nguoi_dang_sua() -> None:
    manager = _user(Role.MANAGER, PHONG_A, "m@congty.vn")
    repo = FakeUserRepository([manager])

    assert await repo.has_active_manager(PHONG_A) is True
    assert await repo.has_active_manager(PHONG_A, exclude_user_id=manager.id) is False


async def test_has_active_manager_bo_qua_manager_da_vo_hieu_hoa() -> None:
    repo = FakeUserRepository([_user(Role.MANAGER, PHONG_A, "m@congty.vn", is_active=False)])

    assert await repo.has_active_manager(PHONG_A) is False


async def test_tim_kiem_khop_ca_ho_ten_va_email() -> None:
    repo = FakeUserRepository([_user(Role.STAFF, PHONG_A, "nguyenvana@congty.vn")])

    assert len(await repo.list_users(search="NGUYENVANA")) == 1
    assert len(await repo.list_users(search="Người")) == 1
    assert len(await repo.list_users(search="khong-ton-tai")) == 0


async def test_get_by_name_bo_qua_phong_ban_da_vo_hieu_hoa() -> None:
    phong = Department.create(name="Kinh doanh", description=None, now=BAY_GIO)
    phong.deactivate(active_member_count=0, now=BAY_GIO)
    repo = FakeDepartmentRepository([phong])

    assert await repo.get_by_name("Kinh doanh") is None


async def test_revoke_chain_thu_hoi_toan_bo_chuoi_token() -> None:
    repo = FakeRefreshTokenRepository()
    dau = RefreshToken.issue(new_id(), "hash1", BAY_GIO, BAY_GIO)
    giua = RefreshToken.issue(new_id(), "hash2", BAY_GIO, BAY_GIO)
    cuoi = RefreshToken.issue(new_id(), "hash3", BAY_GIO, BAY_GIO)
    dau.rotate_to(giua.id, BAY_GIO)
    giua.rotate_to(cuoi.id, BAY_GIO)
    for t in (dau, giua, cuoi):
        await repo.add(t)

    await repo.revoke_chain(dau, now=BAY_GIO)

    assert cuoi.is_revoked() is True
