from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.models.user_model import UserModel
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.shared.domain.identifiers import new_id

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


async def _tao_phong(session: AsyncSession, ten: str) -> Department:
    phong = Department.create(name=ten, description=None, now=BAY_GIO)
    await SqlAlchemyDepartmentRepository(session).add(phong)
    await session.flush()
    return phong


def _user(
    email: str, role: Role, department_id, full_name: str = "Nguyễn Văn A"
) -> User:
    return User.create(
        email=Email(email),
        password_hash=PasswordHash("$2b$12$hash"),
        full_name=full_name,
        role=role,
        department_id=department_id,
        now=BAY_GIO,
    )


class TestLuuVaDoc:
    async def test_luu_roi_doc_lai_duoc_theo_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng 1")
        goc = _user("a@congty.vn", Role.STAFF, phong.id)

        await repo.add(goc)
        await db_session.flush()
        doc_lai = await repo.get_by_id(goc.id)

        assert doc_lai is not None
        assert doc_lai.id == goc.id
        assert doc_lai.email == goc.email
        assert doc_lai.role is Role.STAFF

    async def test_tim_theo_email_khong_phan_biet_hoa_thuong(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng 2")
        # Không đi qua repo.add / mapper: ghi trực tiếp giá trị chữ HOA vào cột.
        db_session.add(
            UserModel(
                id=new_id(),
                email="HoaThuong@CongTy.VN",
                password_hash="$2b$12$hash",
                full_name="Nguyễn Văn A",
                phone=None,
                role=Role.STAFF.value,
                department_id=phong.id,
                is_active=True,
                must_change_password=True,
                last_login_at=None,
                created_at=BAY_GIO,
                updated_at=BAY_GIO,
            )
        )
        await db_session.flush()

        # Value object chuẩn hoá khoá tra cứu về "hoathuong@congty.vn"; chỉ khi
        # truy vấn dùng lower(email) thì mới khớp được với bản ghi chữ HOA.
        assert await repo.get_by_email(Email("hoathuong@congty.vn")) is not None

    async def test_khong_tim_thay_thi_tra_ve_none(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)

        assert await repo.get_by_id(new_id()) is None
        assert await repo.get_by_email(Email("khongton@tai.vn")) is None

    async def test_cap_nhat_duoc_luu_lai(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng 3")
        user = _user("capnhat@congty.vn", Role.STAFF, phong.id)
        await repo.add(user)
        await db_session.flush()

        user.update_profile(full_name="Tên Mới", phone="0911111111", now=BAY_GIO)
        await repo.update(user)
        await db_session.flush()

        doc_lai = await repo.get_by_id(user.id)
        assert doc_lai is not None
        assert doc_lai.full_name == "Tên Mới"
        assert doc_lai.phone == "0911111111"


class TestDemVaKiemTra:
    async def test_dem_nhan_vien_dang_hoat_dong_trong_phong(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Đếm")
        dang_lam = _user("a@congty.vn", Role.STAFF, phong.id)
        nghi_viec = _user("b@congty.vn", Role.STAFF, phong.id)
        nghi_viec.deactivate(is_last_active_admin=False, now=BAY_GIO)
        await repo.add(dang_lam)
        await repo.add(nghi_viec)
        await db_session.flush()

        assert await repo.count_active_in_department(phong.id) == 1

    async def test_phat_hien_phong_da_co_quan_ly(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Quản Lý")
        manager = _user("m@congty.vn", Role.MANAGER, phong.id)
        await repo.add(manager)
        await db_session.flush()

        assert await repo.has_active_manager(phong.id) is True
        assert await repo.has_active_manager(phong.id, exclude_user_id=manager.id) is False

    async def test_quan_ly_da_vo_hieu_hoa_khong_tinh_la_dang_hoat_dong(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Quản Lý Cũ")
        manager = _user("mcu@congty.vn", Role.MANAGER, phong.id)
        manager.deactivate(is_last_active_admin=False, now=BAY_GIO)
        await repo.add(manager)
        await db_session.flush()

        assert await repo.has_active_manager(phong.id) is False

    async def test_dem_quan_tri_vien_dang_hoat_dong(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        truoc = await repo.count_active_admins()
        await repo.add(_user("ad@congty.vn", Role.ADMIN, None))
        await db_session.flush()

        assert await repo.count_active_admins() == truoc + 1


class TestLocVaPhanTrang:
    async def test_loc_theo_phong_ban(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong_a = await _tao_phong(db_session, "Phòng Lọc A")
        phong_b = await _tao_phong(db_session, "Phòng Lọc B")
        await repo.add(_user("a@congty.vn", Role.STAFF, phong_a.id))
        await repo.add(_user("b@congty.vn", Role.STAFF, phong_b.id))
        await db_session.flush()

        ket_qua = await repo.list_users(department_id=phong_a.id)

        assert len(ket_qua) == 1
        assert ket_qua[0].email == Email("a@congty.vn")

    async def test_loc_theo_vai_tro(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Vai Trò")
        await repo.add(_user("s@congty.vn", Role.STAFF, phong.id))
        await repo.add(_user("m@congty.vn", Role.MANAGER, phong.id))
        await db_session.flush()

        ket_qua = await repo.list_users(department_id=phong.id, role=Role.MANAGER)

        assert len(ket_qua) == 1
        assert ket_qua[0].role is Role.MANAGER

    async def test_tim_kiem_khop_ho_ten_khong_phan_biet_hoa_thuong(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Tìm Kiếm")
        await repo.add(
            _user("timkiem@congty.vn", Role.STAFF, phong.id, full_name="Trần Thị Bích")
        )
        await db_session.flush()

        assert len(await repo.list_users(department_id=phong.id, search="trần")) == 1
        assert len(await repo.list_users(department_id=phong.id, search="TIMKIEM")) == 1
        assert len(await repo.list_users(department_id=phong.id, search="xyz")) == 0

    async def test_phan_trang_tra_ve_dung_so_luong(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Phân Trang")
        for i in range(5):
            await repo.add(_user(f"pt{i}@congty.vn", Role.STAFF, phong.id))
        await db_session.flush()

        trang_dau = await repo.list_users(department_id=phong.id, limit=2, offset=0)
        trang_hai = await repo.list_users(department_id=phong.id, limit=2, offset=2)

        assert len(trang_dau) == 2
        assert len(trang_hai) == 2
        assert {u.id for u in trang_dau} & {u.id for u in trang_hai} == set()

    async def test_dem_khop_voi_bo_loc_cua_danh_sach(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Đếm Lọc")
        for i in range(3):
            await repo.add(_user(f"dl{i}@congty.vn", Role.STAFF, phong.id))
        await db_session.flush()

        assert await repo.count_users(department_id=phong.id) == 3
