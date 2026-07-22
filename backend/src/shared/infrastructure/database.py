"""Engine và session factory cho SQLAlchemy async."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Lớp cơ sở khai báo cho mọi ORM model."""


def create_engine_and_session_factory(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Tạo engine async và session factory tương ứng.

    ``expire_on_commit=False`` để đối tượng vẫn đọc được sau khi commit —
    cần thiết vì mapper chuyển ORM model sang domain entity sau khi commit.
    """
    engine = create_async_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine, session_factory
