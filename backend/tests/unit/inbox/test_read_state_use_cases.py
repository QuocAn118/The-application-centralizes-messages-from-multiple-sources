"""BE-1 (chưa đọc theo từng người) + BE-9 (khách đã chờ) ở tầng use case.

SQL đếm/tính thời gian được kiểm trên DB thật ở
``tests/integration/test_inbox_chua_doc.py``; ở đây kiểm quy tắc của use case:
ai được đánh dấu, hội thoại đã đóng không bao giờ "chưa đọc"/"đang chờ", và trả
lời tự đánh dấu đã đọc.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.get_conversation import GetConversation
from src.modules.inbox.application.use_cases.list_inbox import ListInbox
from src.modules.inbox.application.use_cases.read_state import (
    CountUnreadConversations,
    MarkConversationRead,
)
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.domain.value_objects.platform import Platform
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.inbox.fakes import (
    FakeChannelRepository,
    FakeClock,
    FakeConversationRepository,
    FakeCustomerRepository,
    FakeMessageRepository,
    FakeReadRepository,
)

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)
PHONG_A = new_id()
PHONG_B = new_id()


class _Kho:
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
        self.read_repo = FakeReadRepository()
        self.clock = FakeClock(BAY_GIO)

    def them(self, department_id=PHONG_A) -> Conversation:
        khach = Customer.register(
            channel_id=self.channel.id,
            platform=Platform.ZALO,
            external_id=f"c_{new_id()}",
            display_name="Khach",
            now=BAY_GIO,
        )
        self.customer_repo._customers[khach.id] = khach
        ht = Conversation.start(
            channel_id=self.channel.id,
            customer_id=khach.id,
            department_id=department_id,
            now=BAY_GIO,
        )
        self.conversation_repo._conversations[ht.id] = ht
        return ht

    def list_uc(self) -> ListInbox:
        return ListInbox(
            self.conversation_repo, self.customer_repo, self.channel_repo, self.message_repo
        )


def _staff(department_id=PHONG_A) -> InboxActor:
    return InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=department_id)


class TestDanhSachCoChuaDocVaDangCho:
    async def test_tra_so_chua_doc_cua_chinh_nguoi_goi(self) -> None:
        kho, nv = _Kho(), _staff()
        ht = kho.them()
        kho.message_repo.chua_doc[ht.id] = 3

        page = await kho.list_uc().execute(nv)

        assert page.items[0].unread_count == 3
        # Đếm theo TỪNG NGƯỜI: phải hỏi đúng người đang gọi.
        assert kho.message_repo.hoi_chua_doc_cua == nv.user_id

    async def test_tra_waiting_since(self) -> None:
        kho, nv = _Kho(), _staff()
        ht = kho.them()
        luc = BAY_GIO - timedelta(minutes=12)
        kho.message_repo.cho_tu[ht.id] = luc

        page = await kho.list_uc().execute(nv)

        assert page.items[0].waiting_since == luc

    async def test_hoi_thoai_da_dong_khong_chua_doc_khong_cho(self) -> None:
        """Đã xử lý xong: không làm nhiễu danh sách dù repo còn tin vào chưa đọc."""
        kho, nv = _Kho(), _staff()
        ht = kho.them()
        ht.close(BAY_GIO)
        kho.message_repo.chua_doc[ht.id] = 5
        kho.message_repo.cho_tu[ht.id] = BAY_GIO

        page = await kho.list_uc().execute(nv)

        assert page.items[0].unread_count == 0
        assert page.items[0].waiting_since is None

    async def test_chi_tiet_co_waiting_since(self) -> None:
        kho, nv = _Kho(), _staff()
        ht = kho.them()
        kho.message_repo.cho_tu[ht.id] = BAY_GIO
        uc = GetConversation(
            kho.conversation_repo, kho.message_repo, kho.channel_repo, kho.customer_repo
        )

        view = await uc.execute(nv, ht.id)

        assert view.waiting_since == BAY_GIO


class TestDanhDauDaDoc:
    def uc(self, kho: _Kho) -> MarkConversationRead:
        return MarkConversationRead(kho.conversation_repo, kho.read_repo, kho.clock)

    async def test_ghi_moc_cho_dung_nguoi(self) -> None:
        kho, nv = _Kho(), _staff()
        ht = kho.them()

        await self.uc(kho).execute(nv, ht.id)

        assert kho.read_repo.da_doc == [(nv.user_id, ht.id, BAY_GIO)]

    async def test_nguoi_phong_khac_bi_tu_choi(self) -> None:
        """Quyền = quyền xem hội thoại (như GET /inbox/{id})."""
        kho = _Kho()
        ht = kho.them(PHONG_B)

        with pytest.raises(PermissionDeniedError):
            await self.uc(kho).execute(_staff(PHONG_A), ht.id)
        assert kho.read_repo.da_doc == []

    async def test_hoi_thoai_khong_ton_tai(self) -> None:
        kho = _Kho()
        with pytest.raises(NotFoundError):
            await self.uc(kho).execute(_staff(), new_id())


class TestDemHoiThoaiChuaDoc:
    async def test_staff_dung_pham_vi_phong_minh(self) -> None:
        kho, nv = _Kho(), _staff()
        kho.conversation_repo.so_chua_doc = 4

        so = await CountUnreadConversations(kho.conversation_repo).execute(nv)

        assert so == 4
        assert kho.conversation_repo.hoi_dem_chua_doc == ([PHONG_A], False, nv.user_id)

    async def test_admin_khong_gioi_han_phong(self) -> None:
        kho = _Kho()
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        await CountUnreadConversations(kho.conversation_repo).execute(admin)

        assert kho.conversation_repo.hoi_dem_chua_doc == (None, True, admin.user_id)
