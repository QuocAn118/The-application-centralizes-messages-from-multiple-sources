"""BE-1 (chưa đọc theo từng người) + BE-9 (khách đã chờ) trên PostgreSQL thật.

Logic nằm trong SQL (đếm theo lô cho cả trang), nên phải kiểm trên DB thật — fake
in-memory không bắt được lỗi so sánh thời gian hay điều kiện JOIN.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.domain.entities.message import Message
from src.modules.inbox.domain.value_objects.message_content import MessageContent
from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.repositories.channel_repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.inbox.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from src.modules.inbox.infrastructure.repositories.message_repository import (
    SqlAlchemyMessageRepository,
)
from src.modules.inbox.infrastructure.repositories.read_repository import (
    SqlAlchemyReadRepository,
)
from src.shared.domain.identifiers import new_id

pytestmark = pytest.mark.integration

T0 = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)


def phut(n: int) -> datetime:
    return T0 + timedelta(minutes=n)


class _Kho:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session
        self.conv = SqlAlchemyConversationRepository(session)
        self.msg = SqlAlchemyMessageRepository(session)
        self.read = SqlAlchemyReadRepository(session)
        self.phong = new_id()
        self.channel: Channel | None = None

    async def hoi_thoai(self, phong_khac: bool = False) -> Conversation:
        if self.channel is None:
            self.channel = Channel.connect(
                platform=Platform.ZALO,
                external_channel_id=f"oa_{new_id()}",
                name="OA",
                department_id=None,
                encrypted_credential="enc::t",
                now=T0,
            )
            await SqlAlchemyChannelRepository(self.s).add(self.channel)
            await self.s.flush()
        khach = Customer.register(
            channel_id=self.channel.id,
            platform=Platform.ZALO,
            external_id=f"c_{new_id()}",
            display_name="Khach",
            now=T0,
        )
        await SqlAlchemyCustomerRepository(self.s).add(khach)
        await self.s.flush()
        dept = new_id() if phong_khac else self.phong
        cv = Conversation.start(
            channel_id=self.channel.id, customer_id=khach.id, department_id=dept, now=T0
        )
        await self.conv.add(cv)
        await self.s.flush()
        return cv

    async def vao(self, cv: Conversation, luc: datetime) -> None:
        await self.msg.add(
            Message.inbound(cv.id, MessageContent(text="hi"), f"e_{new_id()}", luc), []
        )
        await self.s.flush()

    async def ra(self, cv: Conversation, luc: datetime) -> None:
        await self.msg.add(Message.outbound(cv.id, MessageContent(text="ok"), new_id(), luc), [])
        await self.s.flush()


class TestChuaDoc:
    async def test_chua_mo_lan_nao_thi_dem_moi_tin_vao(self, db_session: AsyncSession) -> None:
        k, toi = _Kho(db_session), new_id()
        cv = await k.hoi_thoai()
        await k.vao(cv, phut(1))
        await k.ra(cv, phut(2))
        await k.vao(cv, phut(3))

        assert await k.msg.unread_counts(toi, [cv.id]) == {cv.id: 2}

    async def test_da_doc_thi_ve_0_tin_moi_thi_tang(self, db_session: AsyncSession) -> None:
        k, toi = _Kho(db_session), new_id()
        cv = await k.hoi_thoai()
        await k.vao(cv, phut(1))
        await k.read.mark_read(toi, cv.id, phut(5))
        await db_session.flush()
        assert await k.msg.unread_counts(toi, [cv.id]) == {}

        await k.vao(cv, phut(6))
        assert await k.msg.unread_counts(toi, [cv.id]) == {cv.id: 1}

    async def test_tin_ra_khong_tinh_la_chua_doc(self, db_session: AsyncSession) -> None:
        k, toi = _Kho(db_session), new_id()
        cv = await k.hoi_thoai()
        await k.ra(cv, phut(1))
        assert await k.msg.unread_counts(toi, [cv.id]) == {}

    async def test_theo_tung_nguoi(self, db_session: AsyncSession) -> None:
        """Quyết định #1: người này đọc không làm mất 'chưa đọc' của người khác."""
        k, toi, ban = _Kho(db_session), new_id(), new_id()
        cv = await k.hoi_thoai()
        await k.vao(cv, phut(1))
        await k.read.mark_read(toi, cv.id, phut(5))
        await db_session.flush()

        assert await k.msg.unread_counts(toi, [cv.id]) == {}
        assert await k.msg.unread_counts(ban, [cv.id]) == {cv.id: 1}

    async def test_danh_dau_lui_thoi_gian_khong_lam_tang_lai(
        self, db_session: AsyncSession
    ) -> None:
        """Hai tab gửi 'đã đọc' lệch nhau: mốc cũ tới sau không được kéo lùi."""
        k, toi = _Kho(db_session), new_id()
        cv = await k.hoi_thoai()
        await k.vao(cv, phut(3))
        await k.read.mark_read(toi, cv.id, phut(5))
        await k.read.mark_read(toi, cv.id, phut(1))
        await db_session.flush()

        assert await k.msg.unread_counts(toi, [cv.id]) == {}

    async def test_dem_theo_lo_nhieu_hoi_thoai(self, db_session: AsyncSession) -> None:
        k, toi = _Kho(db_session), new_id()
        a, b, c = await k.hoi_thoai(), await k.hoi_thoai(), await k.hoi_thoai()
        await k.vao(a, phut(1))
        await k.vao(b, phut(1))
        await k.vao(b, phut(2))

        assert await k.msg.unread_counts(toi, [a.id, b.id, c.id]) == {a.id: 1, b.id: 2}


class TestDemHoiThoaiChuaDoc:
    """Huy hiệu nav: số hội thoại TRONG PHẠM VI có tin chưa đọc; DA_DONG không tính."""

    async def test_dem_theo_pham_vi_va_bo_hoi_thoai_da_dong(self, db_session: AsyncSession) -> None:
        k, toi = _Kho(db_session), new_id()
        mo_chua_doc = await k.hoi_thoai()
        mo_da_doc = await k.hoi_thoai()
        da_dong = await k.hoi_thoai()
        phong_khac = await k.hoi_thoai(phong_khac=True)
        for cv in (mo_chua_doc, mo_da_doc, da_dong, phong_khac):
            await k.vao(cv, phut(1))
        await k.read.mark_read(toi, mo_da_doc.id, phut(5))
        da_dong.close(phut(4))
        await k.conv.update(da_dong)
        await db_session.flush()

        so = await k.conv.count_unread_for_scope([k.phong], False, toi)
        assert so == 1  # chỉ mo_chua_doc


class TestKhachDaCho:
    """BE-9: tin VÀO ĐẦU TIÊN sau tin RA cuối cùng."""

    async def test_khach_nhan_nhieu_tin_thi_tinh_tu_tin_dau(self, db_session: AsyncSession) -> None:
        k = _Kho(db_session)
        cv = await k.hoi_thoai()
        await k.vao(cv, phut(1))
        await k.ra(cv, phut(2))
        await k.vao(cv, phut(3))
        await k.vao(cv, phut(4))
        await k.vao(cv, phut(5))

        assert await k.msg.waiting_since([cv.id]) == {cv.id: phut(3)}

    async def test_tin_cuoi_la_tin_ra_thi_khong_cho(self, db_session: AsyncSession) -> None:
        k = _Kho(db_session)
        cv = await k.hoi_thoai()
        await k.vao(cv, phut(1))
        await k.ra(cv, phut(2))

        assert await k.msg.waiting_since([cv.id]) == {}

    async def test_chua_tra_loi_lan_nao_thi_tu_tin_dau_tien(self, db_session: AsyncSession) -> None:
        k = _Kho(db_session)
        cv = await k.hoi_thoai()
        await k.vao(cv, phut(1))
        await k.vao(cv, phut(2))

        assert await k.msg.waiting_since([cv.id]) == {cv.id: phut(1)}
