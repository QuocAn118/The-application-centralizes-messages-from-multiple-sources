"""BE-2 trên PostgreSQL thật: so-và-đổi người phụ trách + timeline sự kiện."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.entities.conversation_event import (
    ConversationEvent,
    ConversationEventKind,
)
from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.repositories.channel_repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.inbox.infrastructure.repositories.conversation_event_repository import (
    SqlAlchemyConversationEventRepository,
)
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.inbox.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from src.shared.domain.identifiers import new_id

pytestmark = pytest.mark.integration

T0 = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)


async def _hoi_thoai(s: AsyncSession) -> Conversation:
    ch = Channel.connect(
        platform=Platform.ZALO,
        external_channel_id=f"oa_{new_id()}",
        name="OA",
        department_id=None,
        encrypted_credential="enc::t",
        now=T0,
    )
    await SqlAlchemyChannelRepository(s).add(ch)
    await s.flush()
    kh = Customer.register(
        channel_id=ch.id,
        platform=Platform.ZALO,
        external_id=f"c_{new_id()}",
        display_name="Khach",
        now=T0,
    )
    await SqlAlchemyCustomerRepository(s).add(kh)
    await s.flush()
    cv = Conversation.start(channel_id=ch.id, customer_id=kh.id, department_id=new_id(), now=T0)
    await SqlAlchemyConversationRepository(s).add(cv)
    await s.flush()
    return cv


class TestSoVaDoi:
    """Review Focus #1: hai người đổi cùng lúc — một bên thắng, không lệch dữ liệu."""

    async def test_doi_khi_nguoi_cu_con_dung(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyConversationRepository(db_session)
        cv, b = await _hoi_thoai(db_session), new_id()

        ok = await repo.doi_nguoi_phu_trach_neu_chua_doi(cv.id, None, b, T0)
        await db_session.flush()
        db_session.expire_all()

        assert ok is True
        assert (await repo.get_by_id(cv.id)).assigned_user_id == b  # type: ignore[union-attr]

    async def test_ben_den_sau_thua_khong_ghi_de(self, db_session: AsyncSession) -> None:
        """Manager đổi sang B trước; Admin (vẫn tưởng chưa ai) gỡ sau → bị từ chối."""
        repo = SqlAlchemyConversationRepository(db_session)
        cv, b = await _hoi_thoai(db_session), new_id()

        assert await repo.doi_nguoi_phu_trach_neu_chua_doi(cv.id, None, b, T0) is True
        # Bên thứ hai đọc trạng thái cũ (người cũ = None) rồi mới ghi.
        ben_sau = await repo.doi_nguoi_phu_trach_neu_chua_doi(cv.id, None, new_id(), T0)
        await db_session.flush()
        db_session.expire_all()

        assert ben_sau is False
        assert (await repo.get_by_id(cv.id)).assigned_user_id == b  # type: ignore[union-attr]

    async def test_khong_doi_khi_hoi_thoai_da_dong(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyConversationRepository(db_session)
        cv = await _hoi_thoai(db_session)
        cv.close(T0)
        await repo.update(cv)
        await db_session.flush()

        assert await repo.doi_nguoi_phu_trach_neu_chua_doi(cv.id, None, new_id(), T0) is False


class TestTimeline:
    async def test_luu_va_doc_theo_thu_tu_thoi_gian(self, db_session: AsyncSession) -> None:
        cv = await _hoi_thoai(db_session)
        repo = SqlAlchemyConversationEventRepository(db_session)
        a, b, quan_ly = new_id(), new_id(), new_id()
        # Chèn lệch thứ tự để kiểm sắp xếp.
        await repo.add(
            ConversationEvent.ghi(
                cv.id,
                ConversationEventKind.REASSIGNED,
                T0 + timedelta(minutes=5),
                actor_user_id=quan_ly,
                from_user_id=a,
                to_user_id=b,
            )
        )
        await repo.add(
            ConversationEvent.ghi(
                cv.id,
                ConversationEventKind.TAKEN,
                T0,
                actor_user_id=a,
                to_user_id=a,
            )
        )
        await db_session.flush()

        ds = await repo.list_for_conversation(cv.id)

        assert [e.kind for e in ds] == [
            ConversationEventKind.TAKEN,
            ConversationEventKind.REASSIGNED,
        ]
        assert (ds[1].from_user_id, ds[1].to_user_id, ds[1].actor_user_id) == (a, b, quan_ly)

    async def test_chi_tra_su_kien_cua_dung_hoi_thoai(self, db_session: AsyncSession) -> None:
        cv1, cv2 = await _hoi_thoai(db_session), await _hoi_thoai(db_session)
        repo = SqlAlchemyConversationEventRepository(db_session)
        await repo.add(ConversationEvent.ghi(cv1.id, ConversationEventKind.UNASSIGNED, T0))
        await db_session.flush()

        assert await repo.list_for_conversation(cv2.id) == []
