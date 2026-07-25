from datetime import UTC, datetime

import pytest

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.get_conversation import GetConversation
from src.modules.inbox.application.use_cases.list_inbox import ListInbox
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.domain.entities.message import Message
from src.modules.inbox.domain.value_objects.platform import Platform
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.inbox.fakes import (
    FakeChannelRepository,
    FakeConversationRepository,
    FakeCustomerRepository,
    FakeMessageRepository,
)

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)
PHONG_A = new_id()
PHONG_B = new_id()


class _KhoDuLieu:
    """Dựng sẵn 3 hội thoại: phòng A, phòng B, và một cái chờ-phân."""

    def __init__(self) -> None:
        self.channel = Channel.connect(
            platform=Platform.ZALO,
            external_channel_id="oa",
            name="OA",
            department_id=None,
            encrypted_credential="enc::t",
            now=BAY_GIO,
        )
        self.channel_repo = FakeChannelRepository([self.channel])
        self.customer_repo = FakeCustomerRepository()
        self.conversation_repo = FakeConversationRepository()
        self.message_repo = FakeMessageRepository()
        self.ht_a = self._them(PHONG_A)
        self.ht_b = self._them(PHONG_B)
        self.ht_cho = self._them(None)

    def _them(self, department_id) -> Conversation:
        customer = Customer.register(
            channel_id=self.channel.id,
            platform=Platform.ZALO,
            external_id=f"c_{new_id()}",
            display_name="Khach",
            now=BAY_GIO,
        )
        self.customer_repo._customers[customer.id] = customer
        ht = Conversation.start(
            channel_id=self.channel.id,
            customer_id=customer.id,
            department_id=department_id,
            now=BAY_GIO,
        )
        self.conversation_repo._conversations[ht.id] = ht
        return ht

    def list_uc(self) -> ListInbox:
        return ListInbox(self.conversation_repo, self.customer_repo, self.channel_repo)

    def get_uc(self) -> GetConversation:
        return GetConversation(
            self.conversation_repo, self.message_repo, self.channel_repo, self.customer_repo
        )


class TestListPhamVi:
    async def test_staff_chi_thay_phong_minh(self) -> None:
        kho = _KhoDuLieu()
        staff = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)

        page = await kho.list_uc().execute(staff)

        ids = {i.conversation_id for i in page.items}
        assert ids == {kho.ht_a.id}
        assert page.total == 1

    async def test_manager_thay_phong_minh_va_cho_phan(self) -> None:
        kho = _KhoDuLieu()
        manager = InboxActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=PHONG_A)

        page = await kho.list_uc().execute(manager)

        ids = {i.conversation_id for i in page.items}
        assert ids == {kho.ht_a.id, kho.ht_cho.id}

    async def test_admin_thay_tat_ca(self) -> None:
        kho = _KhoDuLieu()
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        page = await kho.list_uc().execute(admin)

        ids = {i.conversation_id for i in page.items}
        assert ids == {kho.ht_a.id, kho.ht_b.id, kho.ht_cho.id}

    async def test_staff_khong_thay_cho_phan(self) -> None:
        kho = _KhoDuLieu()
        staff = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)

        page = await kho.list_uc().execute(staff)

        assert kho.ht_cho.id not in {i.conversation_id for i in page.items}


class TestGetChoPhan:
    async def test_manager_xem_duoc_hoi_thoai_cho_phan(self) -> None:
        kho = _KhoDuLieu()
        manager = InboxActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=PHONG_A)

        view = await kho.get_uc().execute(manager, kho.ht_cho.id)

        assert view.conversation_id == kho.ht_cho.id
        assert view.department_id is None

    async def test_staff_khong_xem_duoc_hoi_thoai_cho_phan(self) -> None:
        kho = _KhoDuLieu()
        staff = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)

        with pytest.raises(PermissionDeniedError):
            await kho.get_uc().execute(staff, kho.ht_cho.id)


class TestGetConversation:
    async def test_xem_hoi_thoai_kem_tin(self) -> None:
        kho = _KhoDuLieu()
        msg = Message.inbound(
            conversation_id=kho.ht_a.id, text="hello", external_message_id="m1", now=BAY_GIO
        )
        await kho.message_repo.add(msg, [])
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        view = await kho.get_uc().execute(admin, kho.ht_a.id)

        assert view.conversation_id == kho.ht_a.id
        assert len(view.messages) == 1
        assert view.messages[0].text == "hello"

    async def test_staff_khac_phong_bi_tu_choi(self) -> None:
        kho = _KhoDuLieu()
        staff = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_B)

        with pytest.raises(PermissionDeniedError):
            await kho.get_uc().execute(staff, kho.ht_a.id)

    async def test_hoi_thoai_khong_ton_tai(self) -> None:
        kho = _KhoDuLieu()
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        with pytest.raises(NotFoundError):
            await kho.get_uc().execute(admin, new_id())
