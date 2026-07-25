"""Round-trip test cho các repository inbox trên PostgreSQL thật.

Xác nhận mapper không mất field và các truy vấn (idempotency, get_open_for,
scope filtering) chạy đúng trên SQL thật — chỗ mà fake in-memory không kiểm được.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.attachment import Attachment
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.domain.entities.message import Message
from src.modules.inbox.domain.value_objects.message_content import (
    AttachmentKind,
    AttachmentRef,
    MessageContent,
)
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
from src.shared.domain.identifiers import new_id

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)


async def _kenh(session: AsyncSession, department_id=None) -> Channel:
    repo = SqlAlchemyChannelRepository(session)
    ch = Channel.connect(
        platform=Platform.ZALO,
        external_channel_id=f"oa_{new_id()}",
        name="OA",
        department_id=department_id,
        encrypted_credential="enc::token",
        now=BAY_GIO,
    )
    await repo.add(ch)
    await session.flush()
    return ch


async def _khach(session: AsyncSession, channel_id) -> Customer:
    repo = SqlAlchemyCustomerRepository(session)
    cu = Customer.register(
        channel_id=channel_id,
        platform=Platform.ZALO,
        external_id=f"c_{new_id()}",
        display_name="Khach",
        now=BAY_GIO,
    )
    await repo.add(cu)
    await session.flush()
    return cu


class TestChannelRoundTrip:
    async def test_luu_va_doc_lai_giu_nguyen_field(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyChannelRepository(db_session)
        phong = new_id()
        goc = Channel.connect(
            platform=Platform.FACEBOOK,
            external_channel_id="page_1",
            name="Fanpage",
            department_id=phong,
            encrypted_credential="enc::secret",
            now=BAY_GIO,
        )
        await repo.add(goc)
        await db_session.flush()

        doc = await repo.get_by_id(goc.id)
        assert doc is not None
        assert doc.platform is Platform.FACEBOOK
        assert doc.external_channel_id == "page_1"
        assert doc.department_id == phong
        assert doc.encrypted_credential == "enc::secret"

    async def test_get_by_external(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyChannelRepository(db_session)
        ch = await _kenh(db_session)

        doc = await repo.get_by_external(Platform.ZALO, ch.external_channel_id)
        assert doc is not None
        assert doc.id == ch.id

    async def test_cap_nhat_luu_lai(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyChannelRepository(db_session)
        ch = await _kenh(db_session)

        ch.rename("Ten Moi", now=BAY_GIO)
        ch.deactivate(now=BAY_GIO)
        await repo.update(ch)
        await db_session.flush()

        doc = await repo.get_by_id(ch.id)
        assert doc is not None
        assert doc.name == "Ten Moi"
        assert doc.is_active is False

    async def test_list_loc_active(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyChannelRepository(db_session)
        active = await _kenh(db_session)
        ngat = await _kenh(db_session)
        ngat.deactivate(now=BAY_GIO)
        await repo.update(ngat)
        await db_session.flush()

        ds = await repo.list_all(is_active=True)
        ids = {c.id for c in ds}
        assert active.id in ids
        assert ngat.id not in ids


class TestCustomerRoundTrip:
    async def test_get_by_external(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCustomerRepository(db_session)
        ch = await _kenh(db_session)
        cu = await _khach(db_session, ch.id)

        doc = await repo.get_by_external(ch.id, cu.external_id)
        assert doc is not None
        assert doc.id == cu.id

    async def test_cap_nhat_ten(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCustomerRepository(db_session)
        ch = await _kenh(db_session)
        cu = await _khach(db_session, ch.id)

        cu.update_profile(display_name="Ten Moi", avatar_url=None, now=BAY_GIO)
        await repo.update(cu)
        await db_session.flush()

        doc = await repo.get_by_id(cu.id)
        assert doc is not None
        assert doc.display_name == "Ten Moi"


class TestConversationRoundTrip:
    async def test_get_open_for_khong_tra_hoi_thoai_da_dong(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyConversationRepository(db_session)
        ch = await _kenh(db_session, department_id=new_id())
        cu = await _khach(db_session, ch.id)
        cv = Conversation.start(
            channel_id=ch.id, customer_id=cu.id, department_id=ch.department_id, now=BAY_GIO
        )
        await repo.add(cv)
        await db_session.flush()

        assert await repo.get_open_for(ch.id, cu.id) is not None

        cv.close(now=BAY_GIO)
        await repo.update(cv)
        await db_session.flush()

        assert await repo.get_open_for(ch.id, cu.id) is None

    async def test_cap_nhat_trang_thai_va_nguoi_gan(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyConversationRepository(db_session)
        ch = await _kenh(db_session, department_id=new_id())
        cu = await _khach(db_session, ch.id)
        cv = Conversation.start(
            channel_id=ch.id, customer_id=cu.id, department_id=ch.department_id, now=BAY_GIO
        )
        await repo.add(cv)
        await db_session.flush()

        nv = new_id()
        cv.assign_to_agent(nv, now=BAY_GIO)
        await repo.update(cv)
        await db_session.flush()

        doc = await repo.get_by_id(cv.id)
        assert doc is not None
        assert doc.assigned_user_id == nv


class TestScopeFiltering:
    """Kiểm SQL scope khớp đúng luật use case — nơi fake không đủ tin."""

    async def _dung_ba_hoi_thoai(
        self, session: AsyncSession, phong_a, phong_b
    ) -> tuple[Conversation, Conversation, Conversation]:
        repo = SqlAlchemyConversationRepository(session)
        ch = await _kenh(session)
        results = []
        for i, dept in enumerate((phong_a, phong_b, None)):
            cu = await _khach(session, ch.id)
            cv = Conversation.start(
                channel_id=ch.id, customer_id=cu.id, department_id=dept, now=BAY_GIO
            )
            # last_message_at khác nhau để kiểm sort.
            cv.last_message_at = BAY_GIO + timedelta(minutes=i)
            await repo.add(cv)
            results.append(cv)
        await session.flush()
        return results[0], results[1], results[2]

    async def test_staff_chi_phong_minh(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyConversationRepository(db_session)
        phong_a, phong_b = new_id(), new_id()
        ht_a, ht_b, ht_cho = await self._dung_ba_hoi_thoai(db_session, phong_a, phong_b)

        ds = await repo.list_for_scope(department_ids=[phong_a], include_awaiting=False)
        ids = {c.id for c in ds}
        assert ht_a.id in ids
        assert ht_b.id not in ids
        assert ht_cho.id not in ids

    async def test_manager_phong_minh_va_cho_phan(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyConversationRepository(db_session)
        phong_a, phong_b = new_id(), new_id()
        ht_a, ht_b, ht_cho = await self._dung_ba_hoi_thoai(db_session, phong_a, phong_b)

        ds = await repo.list_for_scope(department_ids=[phong_a], include_awaiting=True)
        ids = {c.id for c in ds}
        assert ht_a.id in ids
        assert ht_cho.id in ids
        assert ht_b.id not in ids

    async def test_admin_tat_ca(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyConversationRepository(db_session)
        phong_a, phong_b = new_id(), new_id()
        ht_a, ht_b, ht_cho = await self._dung_ba_hoi_thoai(db_session, phong_a, phong_b)

        ds = await repo.list_for_scope(department_ids=None, include_awaiting=True)
        ids = {c.id for c in ds}
        assert {ht_a.id, ht_b.id, ht_cho.id} <= ids
        assert await repo.count_for_scope(department_ids=None, include_awaiting=True) >= 3

    async def test_sort_moi_nhat_len_dau(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyConversationRepository(db_session)
        phong_a, phong_b = new_id(), new_id()
        _, _, ht_cho = await self._dung_ba_hoi_thoai(db_session, phong_a, phong_b)

        ds = await repo.list_for_scope(department_ids=None, include_awaiting=True)
        # ht_cho có last_message_at trễ nhất (i=2) -> phải đứng đầu.
        assert ds[0].id == ht_cho.id


class TestMessageRoundTrip:
    async def test_luu_tin_voi_dinh_kem(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMessageRepository(db_session)
        ch = await _kenh(db_session, department_id=new_id())
        cu = await _khach(db_session, ch.id)
        conv_repo = SqlAlchemyConversationRepository(db_session)
        cv = Conversation.start(
            channel_id=ch.id, customer_id=cu.id, department_id=ch.department_id, now=BAY_GIO
        )
        await conv_repo.add(cv)
        await db_session.flush()

        msg = Message.inbound(
            conversation_id=cv.id,
            content=MessageContent(
                attachments=(AttachmentRef(kind=AttachmentKind.IMAGE, url="u"),)
            ),
            external_message_id="m1",
            now=BAY_GIO,
        )
        att = Attachment.stored(
            message_id=msg.id,
            kind=AttachmentKind.IMAGE,
            stored_path="var/a.jpg",
            now=BAY_GIO,
            content_type="image/jpeg",
            size=100,
        )
        await repo.add(msg, [att])
        await db_session.flush()

        tins = await repo.list_for_conversation(cv.id)
        assert len(tins) == 1
        atts = await repo.list_attachments(msg.id)
        assert len(atts) == 1
        assert atts[0].stored_path == "var/a.jpg"

    async def test_exists_external_idempotency(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyMessageRepository(db_session)
        ch = await _kenh(db_session, department_id=new_id())
        cu = await _khach(db_session, ch.id)
        conv_repo = SqlAlchemyConversationRepository(db_session)
        cv = Conversation.start(
            channel_id=ch.id, customer_id=cu.id, department_id=ch.department_id, now=BAY_GIO
        )
        await conv_repo.add(cv)
        await db_session.flush()

        assert await repo.exists_external("unique_x") is False
        msg = Message.inbound(
            conversation_id=cv.id,
            content=MessageContent(text="hi"),
            external_message_id="unique_x",
            now=BAY_GIO,
        )
        await repo.add(msg, [])
        await db_session.flush()

        assert await repo.exists_external("unique_x") is True
