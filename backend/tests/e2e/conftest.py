"""Fixture cho test đầu-cuối."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.main import create_app


@pytest.fixture
async def app_test(engine: AsyncEngine):  # type: ignore[no-untyped-def]
    """Ứng dụng trỏ vào cơ sở dữ liệu test.

    Ghi đè ``session_factory`` để test không chạm vào dữ liệu phát triển.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    ung_dung = create_app()
    ung_dung.state.engine = engine
    ung_dung.state.session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return ung_dung


@pytest.fixture
async def client(app_test) -> AsyncIterator[AsyncClient]:  # type: ignore[no-untyped-def]
    async with AsyncClient(transport=ASGITransport(app=app_test), base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def don_du_lieu(engine: AsyncEngine) -> AsyncIterator[None]:
    """Xoá sạch dữ liệu trước mỗi test đầu-cuối.

    Test đầu-cuối đi qua nhiều giao dịch nên không dùng được cách rollback như
    test tích hợp; phải dọn bảng một cách tường minh.
    """
    yield
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE attachments, messages, conversations, customers, channels, "
                "audit_logs, refresh_tokens, users, departments RESTART IDENTITY CASCADE"
            )
        )
