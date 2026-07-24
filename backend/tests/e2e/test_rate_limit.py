import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU = "MatKhauDung123"


async def _tao_admin(engine: AsyncEngine) -> None:
    from src.modules.identity.infrastructure.security.password_hasher import (
        BcryptPasswordHasher,
    )
    from src.shared.domain.identifiers import new_id

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, full_name, phone, role, "
                "department_id, is_active, must_change_password, last_login_at, "
                "created_at, updated_at) VALUES (:id, 'admin@congty.vn', :hash, "
                "'Quản trị viên', NULL, 'ADMIN', NULL, true, false, NULL, now(), now())"
            ),
            {"id": new_id(), "hash": BcryptPasswordHasher(rounds=4).hash(MAT_KHAU)},
        )


async def test_thu_sai_nhieu_lan_bi_chan(
    client: AsyncClient, engine: AsyncEngine, app_test
) -> None:
    """Chống dò mật khẩu bằng cách thử liên tục."""
    await _tao_admin(engine)
    from src.shared.infrastructure.clock import SystemClock
    from src.shared.infrastructure.rate_limiter import InMemoryRateLimiter

    app_test.state.login_rate_limiter = InMemoryRateLimiter(
        max_attempts=3, window_seconds=300, clock=SystemClock()
    )

    for _ in range(3):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": "SaiRoi123"},
        )

    phan_hoi = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@congty.vn", "password": "SaiRoi123"},
    )

    assert phan_hoi.status_code == 429
    assert phan_hoi.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


async def test_dang_nhap_dung_xoa_bo_dem(
    client: AsyncClient, engine: AsyncEngine, app_test
) -> None:
    """Gõ nhầm vài lần rồi đăng nhập được thì không bị phạt tiếp."""
    await _tao_admin(engine)
    from src.shared.infrastructure.clock import SystemClock
    from src.shared.infrastructure.rate_limiter import InMemoryRateLimiter

    app_test.state.login_rate_limiter = InMemoryRateLimiter(
        max_attempts=3, window_seconds=300, clock=SystemClock()
    )

    for _ in range(2):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": "SaiRoi123"},
        )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@congty.vn", "password": MAT_KHAU},
    )

    phan_hoi = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@congty.vn", "password": "SaiRoi123"},
    )

    assert phan_hoi.status_code == 400
