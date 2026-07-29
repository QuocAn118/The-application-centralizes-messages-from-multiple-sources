"""Round-trip test cho hạ tầng keyword trên PostgreSQL thật.

Xác nhận mapper không mất field, unique (department, normalized) chặn trùng ở DB,
JSONB terms round-trip, và các cầu nối đọc/ghi inbox + identity chạy trên SQL
thật — chỗ fake in-memory không kiểm được.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import Conversation, ConversationStatus
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
from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)
from src.modules.keyword.domain.entities.keyword import Keyword
from src.modules.keyword.domain.value_objects.extracted_term import ExtractedTerm
from src.modules.keyword.infrastructure.classifier.claude_classifier import (  # noqa: F401
    ClaudeConversationClassifier,
)
from src.modules.keyword.infrastructure.directory.workforce_directory import (
    IdentityWorkforceDirectory,
)
from src.modules.keyword.infrastructure.inbox_bridge.conversation_directory import (
    InboxConversationDirectory,
)
from src.modules.keyword.infrastructure.inbox_bridge.conversation_router import (
    InboxConversationRouter,
)
from src.modules.keyword.infrastructure.repositories.analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from src.modules.keyword.infrastructure.repositories.keyword_repository import (
    SqlAlchemyKeywordRepository,
)
from src.shared.domain.identifiers import new_id
from src.shared.infrastructure.clock import SystemClock

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 7, 29, 10, 0, tzinfo=UTC)


class _FakeNotifier:
    """Notifier giả cho router — chỉ ghi lại lời gọi, không đẩy WebSocket."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def notify_conversation_changed(self, conversation_id, department_id, change) -> None:
        self.calls.append((conversation_id, department_id, change))


async def _phong(session: AsyncSession, active: bool = True) -> Department:
    repo = SqlAlchemyDepartmentRepository(session)
    dept = Department.create(name=f"Phong {new_id()}", description=None, now=BAY_GIO)
    if not active:
        dept.deactivate(active_member_count=0, now=BAY_GIO)
    await repo.add(dept)
    await session.flush()
    return dept


async def _hoi_thoai_cho_phan(session: AsyncSession) -> Conversation:
    ch = Channel.connect(
        platform=Platform.ZALO,
        external_channel_id=f"oa_{new_id()}",
        name="OA",
        department_id=None,
        encrypted_credential="enc::token",
        now=BAY_GIO,
    )
    await SqlAlchemyChannelRepository(session).add(ch)
    await session.flush()
    cu = Customer.register(
        channel_id=ch.id,
        platform=Platform.ZALO,
        external_id=f"c_{new_id()}",
        display_name="Khach",
        now=BAY_GIO,
    )
    await SqlAlchemyCustomerRepository(session).add(cu)
    await session.flush()
    conv = Conversation.start(channel_id=ch.id, customer_id=cu.id, department_id=None, now=BAY_GIO)
    await SqlAlchemyConversationRepository(session).add(conv)
    await session.flush()
    return conv


class TestKeywordRepository:
    async def test_round_trip(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyKeywordRepository(db_session)
        phong = new_id()
        kw = Keyword.create(department_id=phong, text="Bảo Hành", now=BAY_GIO)
        await repo.add(kw)
        await db_session.flush()

        doc = await repo.get_by_id(kw.id)
        assert doc is not None
        assert doc.department_id == phong
        assert doc.text == "Bảo Hành"
        assert doc.normalized == "bao hanh"

    async def test_unique_normalized_theo_phong_chan_trung(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyKeywordRepository(db_session)
        phong = new_id()
        await repo.add(Keyword.create(department_id=phong, text="bảo hành", now=BAY_GIO))
        await db_session.flush()
        # Khác dấu/hoa nhưng cùng normalized -> vi phạm unique.
        await repo.add(Keyword.create(department_id=phong, text="BAO HANH", now=BAY_GIO))
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_cung_normalized_khac_phong_thi_duoc(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyKeywordRepository(db_session)
        a, b = new_id(), new_id()
        await repo.add(Keyword.create(department_id=a, text="bảo hành", now=BAY_GIO))
        await repo.add(Keyword.create(department_id=b, text="bảo hành", now=BAY_GIO))
        await db_session.flush()  # không lỗi

    async def test_list_scope_va_all_active(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyKeywordRepository(db_session)
        a, b = new_id(), new_id()
        await repo.add(Keyword.create(department_id=a, text="bao hanh", now=BAY_GIO))
        await repo.add(Keyword.create(department_id=b, text="khuyen mai", now=BAY_GIO))
        await db_session.flush()

        chi_a = await repo.list_for_departments([a])
        assert {k.department_id for k in chi_a} == {a}
        assert await repo.list_for_departments([]) == []
        tat_ca = await repo.list_all_active()
        assert {k.department_id for k in tat_ca} >= {a, b}

    async def test_update_va_delete(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyKeywordRepository(db_session)
        kw = Keyword.create(department_id=new_id(), text="cu", now=BAY_GIO)
        await repo.add(kw)
        await db_session.flush()

        kw.rename("moi", now=BAY_GIO)
        await repo.update(kw)
        await db_session.flush()
        assert (await repo.get_by_id(kw.id)).text == "moi"  # type: ignore[union-attr]

        await repo.delete(kw.id)
        await db_session.flush()
        assert await repo.get_by_id(kw.id) is None


class TestAnalysisRepository:
    async def test_round_trip_jsonb_terms(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyAnalysisRepository(db_session)
        conv, phong = new_id(), new_id()
        an = ConversationAnalysis.auto_assigned(
            conversation_id=conv,
            extracted_terms=(
                ExtractedTerm(text="bao hanh may giat", normalized="bao hanh may giat"),
            ),
            department_id=phong,
            confidence=Decimal("0.9"),
            now=BAY_GIO,
        )
        await repo.add(an)
        await db_session.flush()

        doc = await repo.get_by_id(an.id)
        assert doc is not None
        assert doc.suggested_department_id == phong
        assert doc.confidence == Decimal("0.900")
        assert doc.extracted_terms[0].text == "bao hanh may giat"

    async def test_list_moi_nhat_truoc_va_scope(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyAnalysisRepository(db_session)
        conv, phong = new_id(), new_id()
        cu = ConversationAnalysis.ambiguous(
            conversation_id=conv,
            extracted_terms=(),
            confidence=Decimal("0.3"),
            now=datetime(2026, 7, 29, 9, 0, tzinfo=UTC),
        )
        moi = ConversationAnalysis.auto_assigned(
            conversation_id=conv,
            extracted_terms=(),
            department_id=phong,
            confidence=Decimal("0.8"),
            now=datetime(2026, 7, 29, 11, 0, tzinfo=UTC),
        )
        await repo.add(cu)
        await repo.add(moi)
        await db_session.flush()

        lich_su = await repo.list_for_conversation(conv)
        assert [a.id for a in lich_su] == [moi.id, cu.id]

        theo_phong = await repo.list_for_departments([phong])
        assert [a.id for a in theo_phong] == [moi.id]
        assert await repo.count_for_departments([phong]) == 1
        assert await repo.list_for_departments([]) == []
        assert await repo.count_for_departments([]) == 0


class TestWorkforceDirectory:
    async def test_department_exists_active(self, db_session: AsyncSession) -> None:
        directory = IdentityWorkforceDirectory(db_session)
        active = await _phong(db_session, active=True)
        inactive = await _phong(db_session, active=False)

        assert await directory.department_exists_active(active.id) is True
        assert await directory.department_exists_active(inactive.id) is False
        assert await directory.department_exists_active(new_id()) is False


class TestConversationDirectory:
    async def test_snapshot_cho_phan_lay_tin_inbound_dau(self, db_session: AsyncSession) -> None:
        conv = await _hoi_thoai_cho_phan(db_session)
        msg_repo = SqlAlchemyMessageRepository(db_session)
        await msg_repo.add(
            Message.inbound(
                conversation_id=conv.id,
                content=MessageContent(text="tin 1 cua khach"),
                external_message_id=f"e_{new_id()}",
                now=datetime(2026, 7, 29, 10, 1, tzinfo=UTC),
            ),
            [],
        )
        await msg_repo.add(
            Message.outbound(
                conversation_id=conv.id,
                content=MessageContent(text="nhan vien tra loi"),
                sender_user_id=new_id(),
                now=datetime(2026, 7, 29, 10, 2, tzinfo=UTC),
            ),
            [],
        )
        await msg_repo.add(
            Message.inbound(
                conversation_id=conv.id,
                content=MessageContent(text="tin 2 cua khach"),
                external_message_id=f"e_{new_id()}",
                now=datetime(2026, 7, 29, 10, 3, tzinfo=UTC),
            ),
            [],
        )
        await db_session.flush()

        snapshot = await InboxConversationDirectory(db_session).get_snapshot(conv.id, 3)
        assert snapshot is not None
        assert snapshot.is_awaiting is True
        # Chỉ tin INBOUND, đúng thứ tự, bỏ tin OUTBOUND.
        assert snapshot.first_texts == ("tin 1 cua khach", "tin 2 cua khach")

    async def test_snapshot_khong_co_hoi_thoai(self, db_session: AsyncSession) -> None:
        snapshot = await InboxConversationDirectory(db_session).get_snapshot(new_id(), 3)
        assert snapshot is None


class TestConversationRouter:
    async def test_phan_cho_phan_thanh_cong(self, db_session: AsyncSession) -> None:
        conv = await _hoi_thoai_cho_phan(db_session)
        phong = await _phong(db_session, active=True)
        router = InboxConversationRouter(db_session, notifier=_FakeNotifier(), clock=SystemClock())

        ok = await router.assign_to_department(conv.id, phong.id)
        assert ok is True

        doc = await SqlAlchemyConversationRepository(db_session).get_by_id(conv.id)
        assert doc is not None
        assert doc.status is ConversationStatus.DANG_MO
        assert doc.department_id == phong.id

    async def test_phan_that_bai_khi_khong_con_cho_phan(self, db_session: AsyncSession) -> None:
        conv = await _hoi_thoai_cho_phan(db_session)
        phong = await _phong(db_session, active=True)
        router = InboxConversationRouter(db_session, notifier=_FakeNotifier(), clock=SystemClock())
        # Phân lần đầu -> DANG_MO; phân lại phải trả False (không ném).
        assert await router.assign_to_department(conv.id, phong.id) is True
        assert await router.assign_to_department(conv.id, phong.id) is False
