from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
HET_HAN = BAY_GIO + timedelta(days=7)


async def _tao_user(db_session: AsyncSession, email: str) -> User:
    phong = Department.create(name=f"Phòng {email}", description=None, now=BAY_GIO)
    await SqlAlchemyDepartmentRepository(db_session).add(phong)
    await db_session.flush()
    user = User.create(
        email=Email(email),
        password_hash=PasswordHash("$2b$12$hash"),
        full_name="Người dùng",
        role=Role.STAFF,
        department_id=phong.id,
        now=BAY_GIO,
    )
    await SqlAlchemyUserRepository(db_session).add(user)
    await db_session.flush()
    return user


async def test_tim_duoc_token_theo_hash(db_session: AsyncSession) -> None:
    user = await _tao_user(db_session, "token1@congty.vn")
    repo = SqlAlchemyRefreshTokenRepository(db_session)
    token = RefreshToken.issue(user.id, "hash_duy_nhat_1", HET_HAN, BAY_GIO)

    await repo.add(token)
    await db_session.flush()

    doc_lai = await repo.get_by_hash("hash_duy_nhat_1")
    assert doc_lai is not None
    assert doc_lai.user_id == user.id


async def test_thu_hoi_moi_token_cua_mot_nguoi_dung(
    db_session: AsyncSession,
) -> None:
    user = await _tao_user(db_session, "token2@congty.vn")
    repo = SqlAlchemyRefreshTokenRepository(db_session)
    for i in range(3):
        await repo.add(RefreshToken.issue(user.id, f"hash_thu_hoi_{i}", HET_HAN, BAY_GIO))
    await db_session.flush()

    await repo.revoke_all_for_user(user.id, now=BAY_GIO + timedelta(hours=1))
    await db_session.flush()

    for i in range(3):
        token = await repo.get_by_hash(f"hash_thu_hoi_{i}")
        assert token is not None
        assert token.is_revoked() is True


async def test_thu_hoi_toan_bo_chuoi_token(db_session: AsyncSession) -> None:
    """Khi phát hiện token bị tái sử dụng, cả chuỗi phải mất hiệu lực."""
    user = await _tao_user(db_session, "token3@congty.vn")
    repo = SqlAlchemyRefreshTokenRepository(db_session)
    dau = RefreshToken.issue(user.id, "chuoi_dau", HET_HAN, BAY_GIO)
    giua = RefreshToken.issue(user.id, "chuoi_giua", HET_HAN, BAY_GIO)
    cuoi = RefreshToken.issue(user.id, "chuoi_cuoi", HET_HAN, BAY_GIO)
    dau.rotate_to(giua.id, BAY_GIO)
    giua.rotate_to(cuoi.id, BAY_GIO)
    for t in (dau, giua, cuoi):
        await repo.add(t)
    await db_session.flush()

    await repo.revoke_chain(dau, now=BAY_GIO + timedelta(hours=1))
    await db_session.flush()

    ban_cuoi = await repo.get_by_hash("chuoi_cuoi")
    assert ban_cuoi is not None
    assert ban_cuoi.is_revoked() is True
