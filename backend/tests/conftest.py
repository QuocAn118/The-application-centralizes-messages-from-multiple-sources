"""Fixture dùng chung cho toàn bộ test."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.shared.infrastructure.config import get_settings
from src.shared.infrastructure.database import create_engine_and_session_factory
from src.shared.infrastructure.event_loop import cau_hinh_event_loop

# Phải chạy trước khi pytest-asyncio tạo event loop đầu tiên, nếu không psycopg
# sẽ từ chối chạy trên ProactorEventLoop của Windows.
cau_hinh_event_loop()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return get_settings().test_database_url


@pytest.fixture(scope="session")
async def engine(test_database_url: str) -> AsyncIterator[AsyncEngine]:
    engine, _ = create_engine_and_session_factory(test_database_url)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Session bị rollback sau mỗi test, nên các test không ảnh hưởng lẫn nhau."""
    async with session_factory() as session:
        yield session
        await session.rollback()
