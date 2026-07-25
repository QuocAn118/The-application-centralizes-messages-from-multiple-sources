from datetime import UTC, datetime

import pytest

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.reply_to_conversation import (
    ReplyToConversation,
)
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.domain.entities.message import MessageDirection
from src.modules.inbox.domain.value_objects.message_content import MessageContent
from src.modules.inbox.domain.value_objects.platform import Platform
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.inbox.fakes import (
    FakeChannelAdapter,
    FakeChannelAdapterRegistry,
    FakeChannelRepository,
    FakeClock,
    FakeConversationRepository,
    FakeCredentialCipher,
    FakeCustomerRepository,
    FakeMessageRepository,
    FakeRealtimeNotifier,
)

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)
PHONG_A = new_id()


class _BoiCanh:
    def __init__(self, department_id=PHONG_A) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.adapter = FakeChannelAdapter(Platform.ZALO)
        self.channel = Channel.connect(
            platform=Platform.ZALO,
            external_channel_id="oa_1",
            name="OA",
            department_id=department_id,
            encrypted_credential="enc::token",
            now=BAY_GIO,
        )
        self.customer = Customer.register(
            channel_id=self.channel.id,
            platform=Platform.ZALO,
            external_id="cust_1",
            display_name="Khach",
            now=BAY_GIO,
        )
        self.conversation = Conversation.start(
            channel_id=self.channel.id,
            customer_id=self.customer.id,
            department_id=department_id,
            now=BAY_GIO,
        )
        self.channel_repo = FakeChannelRepository([self.channel])
        self.customer_repo = FakeCustomerRepository()
        self.conversation_repo = FakeConversationRepository()
        self.message_repo = FakeMessageRepository()
        self.notifier = FakeRealtimeNotifier()
        self.use_case = ReplyToConversation(
            conversation_repo=self.conversation_repo,
            channel_repo=self.channel_repo,
            customer_repo=self.customer_repo,
            message_repo=self.message_repo,
            adapters=FakeChannelAdapterRegistry([self.adapter]),
            cipher=FakeCredentialCipher(),
            notifier=self.notifier,
            clock=self.clock,
        )

    async def seed(self) -> None:
        await self.customer_repo.add(self.customer)
        await self.conversation_repo.add(self.conversation)


def _nhan_vien(department_id=PHONG_A) -> InboxActor:
    return InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=department_id)


class TestGuiThanhCong:
    async def test_goi_adapter_va_luu_tin_outbound(self) -> None:
        bc = _BoiCanh()
        await bc.seed()

        view = await bc.use_case.execute(
            _nhan_vien(), bc.conversation.id, MessageContent(text="chao ban")
        )

        assert view.direction is MessageDirection.OUTBOUND
        assert view.text == "chao ban"
        # Adapter đã được gọi đúng khách.
        assert bc.adapter.sent == [("cust_1", MessageContent(text="chao ban"))]
        assert len(bc.message_repo.messages) == 1
        assert len(bc.notifier.signals) == 1

    async def test_tin_di_ghi_nguoi_gui(self) -> None:
        bc = _BoiCanh()
        await bc.seed()
        nv = _nhan_vien()

        view = await bc.use_case.execute(nv, bc.conversation.id, MessageContent(text="hi"))

        assert view.sender_user_id == nv.user_id


class TestPhanQuyen:
    async def test_nhan_vien_khac_phong_bi_tu_choi(self) -> None:
        bc = _BoiCanh(department_id=PHONG_A)
        await bc.seed()
        nguoi_la = _nhan_vien(department_id=new_id())

        with pytest.raises(PermissionDeniedError):
            await bc.use_case.execute(nguoi_la, bc.conversation.id, MessageContent(text="x"))

        # Không gọi adapter, không lưu tin.
        assert bc.adapter.sent == []
        assert len(bc.message_repo.messages) == 0

    async def test_admin_tra_loi_duoc_moi_hoi_thoai(self) -> None:
        bc = _BoiCanh(department_id=PHONG_A)
        await bc.seed()
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        view = await bc.use_case.execute(admin, bc.conversation.id, MessageContent(text="ok"))

        assert view.text == "ok"


class TestKhongTonTai:
    async def test_hoi_thoai_khong_ton_tai(self) -> None:
        bc = _BoiCanh()
        await bc.seed()

        with pytest.raises(NotFoundError):
            await bc.use_case.execute(_nhan_vien(), new_id(), MessageContent(text="x"))
