"""Script một lần ``danh_dau_da_doc_khi_trien_khai`` trên PostgreSQL thật (DB test).

Kiểm câu SQL trong session rollback (không để lại dữ liệu), và chế độ CHẠY THỬ
không ghi gì (engine riêng, như script chạy thật).
"""

from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.danh_dau_da_doc_khi_trien_khai import CAU_GHI, chay
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.inbox.infrastructure.repositories.read_repository import (
    SqlAlchemyReadRepository,
)
from tests.integration.test_assignment_bridges import _nhan_vien, _phong
from tests.integration.test_inbox_nguoi_phu_trach import T0, _hoi_thoai

pytestmark = pytest.mark.integration

MOC = T0 + timedelta(days=1)


async def _moc_doc(s: AsyncSession, user_id: UUID, conv_id: UUID):  # type: ignore[no-untyped-def]
    return (
        await s.execute(
            text(
                "SELECT last_read_at FROM conversation_reads "
                "WHERE user_id = :u AND conversation_id = :c"
            ),
            {"u": user_id, "c": conv_id},
        )
    ).scalar_one_or_none()


class TestCauGhi:
    async def test_ghi_cho_nguoi_hoat_dong_x_hoi_thoai_chua_dong(
        self, db_session: AsyncSession
    ) -> None:
        phong = await _phong(db_session)
        a = await _nhan_vien(db_session, phong.id)
        nghi = await _nhan_vien(db_session, phong.id)
        nghi.deactivate(is_last_active_admin=False, now=T0)
        await SqlAlchemyUserRepository(db_session).update(nghi)
        mo, dong = await _hoi_thoai(db_session), await _hoi_thoai(db_session)
        dong.close(T0)
        await SqlAlchemyConversationRepository(db_session).update(dong)
        await db_session.flush()

        await db_session.execute(text(CAU_GHI), {"moc": MOC})

        assert await _moc_doc(db_session, a.id, mo.id) == MOC
        assert await _moc_doc(db_session, a.id, dong.id) is None  # đã đóng: bỏ qua
        assert await _moc_doc(db_session, nghi.id, mo.id) is None  # vô hiệu hoá: bỏ qua

    async def test_khong_lui_moc_moi_hon(self, db_session: AsyncSession) -> None:
        phong = await _phong(db_session)
        a = await _nhan_vien(db_session, phong.id, Role.MANAGER)
        cv = await _hoi_thoai(db_session)
        moi_hon = MOC + timedelta(hours=2)
        await SqlAlchemyReadRepository(db_session).mark_read(a.id, cv.id, moi_hon)
        await db_session.flush()

        await db_session.execute(text(CAU_GHI), {"moc": MOC})

        assert await _moc_doc(db_session, a.id, cv.id) == moi_hon


class TestChayThu:
    async def test_chay_thu_dem_dung_ma_khong_ghi_gi(
        self,
        session_factory,
        test_database_url: str,  # type: ignore[no-untyped-def]
    ) -> None:
        """Script dùng kết nối RIÊNG → dữ liệu phải được COMMIT thật; dọn ở ``finally``."""
        async with session_factory() as s:
            phong = await _phong(s)
            a = await _nhan_vien(s, phong.id)
            cv = await _hoi_thoai(s)
            await s.commit()
        dem = text("SELECT count(*) FROM conversation_reads WHERE user_id = :u")
        engine = create_engine(test_database_url)
        try:
            with engine.connect() as c:
                truoc = c.execute(dem, {"u": a.id}).scalar_one()

            so = chay(test_database_url, ghi=False, moc=MOC)

            with engine.connect() as c:
                sau = c.execute(dem, {"u": a.id}).scalar_one()
            assert so >= 1  # có ít nhất cặp (a, cv) để ghi
            assert (truoc, sau) == (0, 0)  # chạy thử: rollback, không ghi gì
        finally:
            engine.dispose()
            async with session_factory() as s:
                for cau, ma in (
                    ("DELETE FROM conversations WHERE id = :x", cv.id),
                    ("DELETE FROM customers WHERE id = :x", cv.customer_id),
                    ("DELETE FROM channels WHERE id = :x", cv.channel_id),
                    ("DELETE FROM users WHERE id = :x", a.id),
                    ("DELETE FROM departments WHERE id = :x", phong.id),
                ):
                    await s.execute(text(cau), {"x": ma})
                await s.commit()
