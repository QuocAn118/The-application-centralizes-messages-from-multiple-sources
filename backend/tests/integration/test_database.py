import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.shared.infrastructure.sqlalchemy_uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def test_ket_noi_duoc_toi_postgres(db_session: AsyncSession) -> None:
    ket_qua = await db_session.execute(text("SELECT 1"))

    assert ket_qua.scalar_one() == 1


async def test_postgres_dung_phien_ban_17_tro_len(db_session: AsyncSession) -> None:
    ket_qua = await db_session.execute(text("SHOW server_version_num"))
    phien_ban = int(ket_qua.scalar_one())

    assert phien_ban >= 170000


async def test_unit_of_work_commit_thi_du_lieu_duoc_luu(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.session.execute(
            text("CREATE TEMP TABLE thu_nghiem (gia_tri int) ON COMMIT PRESERVE ROWS")
        )
        await uow.session.execute(text("INSERT INTO thu_nghiem VALUES (42)"))
        await uow.commit()

        ket_qua = await uow.session.execute(text("SELECT gia_tri FROM thu_nghiem"))
        assert ket_qua.scalar_one() == 42


async def test_unit_of_work_tu_rollback_khi_co_ngoai_le(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    class LoiGiaLapError(Exception):
        pass

    with pytest.raises(LoiGiaLapError):
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.session.execute(text("CREATE TEMP TABLE thu_nghiem_2 (gia_tri int)"))
            await uow.session.execute(text("INSERT INTO thu_nghiem_2 VALUES (1)"))
            raise LoiGiaLapError

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        ket_qua = await uow.session.execute(
            text("SELECT to_regclass('pg_temp.thu_nghiem_2') IS NULL")
        )
        assert ket_qua.scalar_one() is True
