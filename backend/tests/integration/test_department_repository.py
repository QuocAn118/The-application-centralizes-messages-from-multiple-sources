from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


async def test_luu_roi_doc_lai_duoc(db_session: AsyncSession) -> None:
    repo = SqlAlchemyDepartmentRepository(db_session)
    goc = Department.create(name="Kinh doanh", description="Mô tả", now=BAY_GIO)

    await repo.add(goc)
    await db_session.flush()

    doc_lai = await repo.get_by_id(goc.id)
    assert doc_lai is not None
    assert doc_lai.name == "Kinh doanh"
    assert doc_lai.description == "Mô tả"


async def test_tim_theo_ten_khong_phan_biet_hoa_thuong(
    db_session: AsyncSession,
) -> None:
    repo = SqlAlchemyDepartmentRepository(db_session)
    await repo.add(Department.create(name="Chăm Sóc", description=None, now=BAY_GIO))
    await db_session.flush()

    assert await repo.get_by_name("chăm sóc") is not None


async def test_khong_tim_thay_phong_ban_da_vo_hieu_hoa(
    db_session: AsyncSession,
) -> None:
    repo = SqlAlchemyDepartmentRepository(db_session)
    phong = Department.create(name="Đã Đóng", description=None, now=BAY_GIO)
    phong.deactivate(active_member_count=0, now=BAY_GIO)
    await repo.add(phong)
    await db_session.flush()

    assert await repo.get_by_name("Đã Đóng") is None


async def test_loc_theo_trang_thai_hoat_dong(db_session: AsyncSession) -> None:
    repo = SqlAlchemyDepartmentRepository(db_session)
    dang_mo = Department.create(name="Đang Mở", description=None, now=BAY_GIO)
    da_dong = Department.create(name="Đóng Rồi", description=None, now=BAY_GIO)
    da_dong.deactivate(active_member_count=0, now=BAY_GIO)
    await repo.add(dang_mo)
    await repo.add(da_dong)
    await db_session.flush()

    dang_hoat_dong = await repo.list_departments(is_active=True)

    assert dang_mo.id in {d.id for d in dang_hoat_dong}
    assert da_dong.id not in {d.id for d in dang_hoat_dong}


async def test_cap_nhat_duoc_luu_lai(db_session: AsyncSession) -> None:
    repo = SqlAlchemyDepartmentRepository(db_session)
    phong = Department.create(name="Tên Cũ", description=None, now=BAY_GIO)
    await repo.add(phong)
    await db_session.flush()

    phong.rename("Tên Mới", now=BAY_GIO)
    await repo.update(phong)
    await db_session.flush()

    doc_lai = await repo.get_by_id(phong.id)
    assert doc_lai is not None
    assert doc_lai.name == "Tên Mới"
