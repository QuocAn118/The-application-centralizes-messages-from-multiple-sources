"""Integration test cho IdentityWorkforceDirectory — cầu nối inbox → identity.

Tạo phòng ban + nhân viên thật qua identity, rồi đọc lại qua directory và xác
nhận dịch đúng sang AgentInfo trung lập.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.inbox.infrastructure.directory.workforce_directory import (
    IdentityWorkforceDirectory,
)
from src.shared.domain.identifiers import new_id

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)
_HASH = PasswordHash("$2b$12$" + "a" * 53)


async def _phong(session: AsyncSession, ten: str, active: bool = True) -> Department:
    repo = SqlAlchemyDepartmentRepository(session)
    p = Department.create(name=ten, description=None, now=BAY_GIO)
    if not active:
        p.deactivate(active_member_count=0, now=BAY_GIO)
    await repo.add(p)
    await session.flush()
    return p


async def _nhan_vien(session: AsyncSession, department_id, role: Role = Role.STAFF) -> User:
    repo = SqlAlchemyUserRepository(session)
    u = User.create(
        email=Email(f"{new_id().hex}@x.vn"),
        password_hash=_HASH,
        full_name="Nhan Vien",
        role=role,
        department_id=department_id,
        now=BAY_GIO,
    )
    await repo.add(u)
    await session.flush()
    return u


class TestGetAgent:
    async def test_doc_duoc_nhan_vien(self, db_session: AsyncSession) -> None:
        directory = IdentityWorkforceDirectory(db_session)
        phong = await _phong(db_session, "KD")
        nv = await _nhan_vien(db_session, phong.id, role=Role.STAFF)

        agent = await directory.get_agent(nv.id)

        assert agent is not None
        assert agent.user_id == nv.id
        assert agent.department_id == phong.id
        assert agent.role == "STAFF"
        assert agent.is_active is True

    async def test_khong_co_nhan_vien_tra_none(self, db_session: AsyncSession) -> None:
        directory = IdentityWorkforceDirectory(db_session)

        assert await directory.get_agent(new_id()) is None


class TestDepartmentExistsActive:
    async def test_phong_dang_hoat_dong(self, db_session: AsyncSession) -> None:
        directory = IdentityWorkforceDirectory(db_session)
        phong = await _phong(db_session, "Dang Mo")

        assert await directory.department_exists_active(phong.id) is True

    async def test_phong_da_vo_hieu_hoa(self, db_session: AsyncSession) -> None:
        directory = IdentityWorkforceDirectory(db_session)
        phong = await _phong(db_session, "Da Dong", active=False)

        assert await directory.department_exists_active(phong.id) is False

    async def test_phong_khong_ton_tai(self, db_session: AsyncSession) -> None:
        directory = IdentityWorkforceDirectory(db_session)

        assert await directory.department_exists_active(new_id()) is False
