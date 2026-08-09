from datetime import UTC, datetime

import pytest

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.get_conversation import GetConversation
from src.modules.inbox.application.use_cases.list_inbox import ListInbox
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.domain.entities.message import Message
from src.modules.inbox.domain.value_objects.message_content import MessageContent
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

    def _them(self, department_id, display_name: str = "Khach") -> Conversation:
        customer = Customer.register(
            channel_id=self.channel.id,
            platform=Platform.ZALO,
            external_id=f"c_{new_id()}",
            display_name=display_name,
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
        self.conversation_repo.dat_ten_khach(customer.id, display_name)
        return ht

    def list_uc(self) -> ListInbox:
        return ListInbox(self.conversation_repo, self.customer_repo, self.channel_repo)

    def get_uc(self) -> GetConversation:
        return GetConversation(
            self.conversation_repo, self.message_repo, self.channel_repo, self.customer_repo
        )


class TestListTimKiem:
    """Lọc theo tên khách (``q``).

    Điều quan trọng nhất: tìm kiếm KHÔNG được nới rộng phạm vi quyền — gõ đúng
    tên một khách của phòng khác vẫn không thấy gì.
    """

    async def test_tim_theo_ten_khach(self) -> None:
        kho = _KhoDuLieu()
        ht = kho._them(PHONG_A, display_name="Nguyễn Thị Mai")
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        page = await kho.list_uc().execute(admin, q="Mai")

        assert {i.conversation_id for i in page.items} == {ht.id}
        assert page.total == 1

    async def test_khong_phan_biet_hoa_thuong(self) -> None:
        kho = _KhoDuLieu()
        ht = kho._them(PHONG_A, display_name="Trần Văn Hùng")
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        page = await kho.list_uc().execute(admin, q="trần văn")

        assert {i.conversation_id for i in page.items} == {ht.id}

    async def test_khong_khop_thi_tra_rong(self) -> None:
        kho = _KhoDuLieu()
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        page = await kho.list_uc().execute(admin, q="khong-ai-ten-nay")

        assert page.items == []
        assert page.total == 0

    async def test_chuoi_rong_coi_nhu_khong_tim(self) -> None:
        """Xoá trắng ô tìm kiếm phải trở về danh sách đầy đủ."""
        kho = _KhoDuLieu()
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        for tu_khoa in (None, "", "   "):
            page = await kho.list_uc().execute(admin, q=tu_khoa)
            assert page.total == 3, f"q={tu_khoa!r} không nên lọc gì"

    async def test_tim_kiem_khong_noi_rong_pham_vi_quyen(self) -> None:
        """Staff gõ đúng tên khách của phòng khác vẫn không thấy."""
        kho = _KhoDuLieu()
        ht_phong_khac = kho._them(PHONG_B, display_name="Khach Phong B")
        staff = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)

        page = await kho.list_uc().execute(staff, q="Khach Phong B")

        ids = {i.conversation_id for i in page.items}
        assert ht_phong_khac.id not in ids
        assert page.total == 0


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


class TestGetLayTinMoiNhat:
    """Hội thoại dài hơn ``limit`` phải trả tin MỚI NHẤT, không phải cũ nhất.

    Lấy từ đầu danh sách nghĩa là người dùng mở hội thoại 200 tin chỉ thấy 100
    tin đầu tiên và không bao giờ tới được tin vừa nhận — đúng thứ họ cần đọc.
    """

    async def _dung_hoi_thoai_dai(self, kho: "_KhoDuLieu", so_tin: int) -> None:
        from datetime import timedelta

        for i in range(so_tin):
            await kho.message_repo.add(
                Message.inbound(
                    conversation_id=kho.ht_a.id,
                    content=MessageContent(text=f"tin-{i}"),
                    external_message_id=f"m{i}",
                    now=BAY_GIO + timedelta(minutes=i),
                ),
                [],
            )

    async def test_tra_ve_tin_moi_nhat_khi_hoi_thoai_dai(self) -> None:
        kho = _KhoDuLieu()
        await self._dung_hoi_thoai_dai(kho, 10)
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        view = await kho.get_uc().execute(admin, kho.ht_a.id, limit=3)

        texts = [m.text for m in view.messages]
        assert texts == ["tin-7", "tin-8", "tin-9"], texts

    async def test_van_xep_cu_truoc_moi_sau(self) -> None:
        """Lấy tin mới nhất nhưng hiển thị vẫn theo chiều đọc của khung chat."""
        kho = _KhoDuLieu()
        await self._dung_hoi_thoai_dai(kho, 5)
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        view = await kho.get_uc().execute(admin, kho.ht_a.id, limit=5)

        moc = [m.created_at for m in view.messages]
        assert moc == sorted(moc)

    async def test_newest_false_van_lay_tu_dau(self) -> None:
        kho = _KhoDuLieu()
        await self._dung_hoi_thoai_dai(kho, 10)
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        view = await kho.get_uc().execute(admin, kho.ht_a.id, limit=3, newest=False)

        assert [m.text for m in view.messages] == ["tin-0", "tin-1", "tin-2"]


class TestGetConversation:
    async def test_xem_hoi_thoai_kem_tin(self) -> None:
        kho = _KhoDuLieu()
        msg = Message.inbound(
            conversation_id=kho.ht_a.id,
            content=MessageContent(text="hello"),
            external_message_id="m1",
            now=BAY_GIO,
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
