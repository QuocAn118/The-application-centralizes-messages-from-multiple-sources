from datetime import UTC, datetime

import pytest

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.reply_to_conversation import (
    ChannelInactiveError,
    ReplyToConversation,
)
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import Conversation, NotOpenError
from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.domain.entities.message import MessageDirection
from src.modules.inbox.domain.value_objects.message_content import (
    AttachmentKind,
    AttachmentRef,
    MessageContent,
)
from src.modules.inbox.domain.value_objects.platform import Platform
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.inbox.fakes import (
    FakeAttachmentStore,
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
    def __init__(self, department_id=PHONG_A, is_active=True) -> None:
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
        if not is_active:
            self.channel.deactivate(BAY_GIO)
        self.customer = Customer.register(
            channel_id=self.channel.id,
            platform=Platform.ZALO,
            external_id="cust_1",
            display_name="Khach",
            now=BAY_GIO,
        )
        # department_id set -> hội thoại vào DANG_MO ngay, hợp lệ để trả lời.
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
        self.store = FakeAttachmentStore()
        self.notifier = FakeRealtimeNotifier()
        self.use_case = ReplyToConversation(
            conversation_repo=self.conversation_repo,
            channel_repo=self.channel_repo,
            customer_repo=self.customer_repo,
            message_repo=self.message_repo,
            adapters=FakeChannelAdapterRegistry([self.adapter]),
            cipher=FakeCredentialCipher(),
            attachment_store=self.store,
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

    async def test_adapter_nhan_token_da_giai_ma_khong_phai_ban_ma_hoa(self) -> None:
        # Kênh lưu "enc::token"; adapter phải nhận "token" (đã giải mã), không
        # phải chuỗi mã hoá — nếu không, gửi thật sẽ hỏng auth.
        bc = _BoiCanh()
        await bc.seed()

        await bc.use_case.execute(_nhan_vien(), bc.conversation.id, MessageContent(text="hi"))

        assert bc.adapter.sent_tokens == ["token"]
        assert "enc::" not in bc.adapter.sent_tokens[0]


class TestDinhKemDi:
    async def test_anh_gui_di_duoc_luu_lai(self) -> None:
        bc = _BoiCanh()
        await bc.seed()
        content = MessageContent(
            text="anh day",
            attachments=(
                AttachmentRef(kind=AttachmentKind.IMAGE, url="", content_type="image/png"),
            ),
        )

        view = await bc.use_case.execute(
            _nhan_vien(), bc.conversation.id, content, raw_attachments=[b"png-bytes"]
        )

        assert len(view.attachments) == 1
        assert view.attachments[0].kind is AttachmentKind.IMAGE
        # Đính kèm gửi đi được lưu lại (RB-4), không bị vứt.
        assert bc.store.saved == [b"png-bytes"]

    async def test_lech_so_luong_dinh_kem_no_ngay(self) -> None:
        bc = _BoiCanh()
        await bc.seed()
        content = MessageContent(
            text=None,
            attachments=(AttachmentRef(kind=AttachmentKind.IMAGE, url=""),),
        )

        # content khai 1 ảnh nhưng router không đưa bytes -> lỗi, không mất âm thầm.
        with pytest.raises(ValueError):
            await bc.use_case.execute(_nhan_vien(), bc.conversation.id, content, raw_attachments=[])


class TestTrangThai:
    async def test_khong_tra_loi_hoi_thoai_cho_phan(self) -> None:
        # Kênh không gắn phòng -> hội thoại CHO_PHAN; Manager xem được nhưng
        # không được trả lời khi chưa phân phòng.
        bc = _BoiCanh(department_id=None)
        await bc.seed()
        manager = InboxActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=PHONG_A)

        with pytest.raises(NotOpenError):
            await bc.use_case.execute(manager, bc.conversation.id, MessageContent(text="x"))

        assert bc.adapter.sent == []
        assert len(bc.message_repo.messages) == 0

    async def test_khong_tra_loi_hoi_thoai_da_dong(self) -> None:
        bc = _BoiCanh()
        await bc.seed()
        bc.conversation.close(BAY_GIO)
        await bc.conversation_repo.update(bc.conversation)

        with pytest.raises(NotOpenError):
            await bc.use_case.execute(_nhan_vien(), bc.conversation.id, MessageContent(text="x"))


class TestKenhNgat:
    async def test_khong_gui_qua_kenh_da_ngat(self) -> None:
        bc = _BoiCanh(is_active=False)
        await bc.seed()

        with pytest.raises(ChannelInactiveError):
            await bc.use_case.execute(_nhan_vien(), bc.conversation.id, MessageContent(text="x"))

        assert bc.adapter.sent == []


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


class TestGuiKemAnh:
    """Gửi ảnh đính kèm (nợ (a) đã trả).

    Điểm dễ sai nhất là THỨ TỰ: Zalo/Meta không nhận nội dung tệp trực tiếp mà
    tự tải về từ URL ta cung cấp, nên ảnh phải được lưu và có URL TRƯỚC khi gọi
    adapter. Làm ngược lại thì adapter nhận URL rỗng và khách không thấy ảnh.
    """

    @staticmethod
    def _boi_canh_co_url() -> "_BoiCanh":
        bc = _BoiCanh()
        bc.use_case = ReplyToConversation(
            conversation_repo=bc.conversation_repo,
            channel_repo=bc.channel_repo,
            customer_repo=bc.customer_repo,
            message_repo=bc.message_repo,
            adapters=FakeChannelAdapterRegistry([bc.adapter]),
            cipher=FakeCredentialCipher(),
            attachment_store=bc.store,
            notifier=bc.notifier,
            clock=bc.clock,
            public_url=lambda aid, cid: f"https://vidu.test/f/{cid}/{aid}",
        )
        return bc

    async def test_anh_duoc_luu_va_adapter_nhan_url_da_co(self) -> None:
        bc = self._boi_canh_co_url()
        await bc.seed()

        view = await bc.use_case.execute(
            _nhan_vien(),
            bc.conversation.id,
            MessageContent(
                text="anh day",
                attachments=(AttachmentRef(kind=AttachmentKind.IMAGE, content_type="image/png"),),
            ),
            raw_attachments=[b"noi-dung-png"],
        )

        # Tệp đã xuống store.
        assert bc.store.saved == [b"noi-dung-png"]
        # Adapter nhận URL TUYỆT ĐỐI trỏ tới tệp vừa lưu — không phải chuỗi rỗng.
        _, noi_dung_gui = bc.adapter.sent[0]
        assert len(noi_dung_gui.attachments) == 1
        assert noi_dung_gui.attachments[0].url.startswith("https://vidu.test/f/")
        assert noi_dung_gui.text == "anh day"
        # Tin lưu lại có đính kèm để lịch sử hội thoại không mất ảnh.
        assert len(view.attachments) == 1

    async def test_gui_anh_khong_kem_text(self) -> None:
        bc = self._boi_canh_co_url()
        await bc.seed()

        view = await bc.use_case.execute(
            _nhan_vien(),
            bc.conversation.id,
            MessageContent(
                attachments=(AttachmentRef(kind=AttachmentKind.IMAGE, content_type="image/png"),)
            ),
            raw_attachments=[b"chi-co-anh"],
        )

        assert view.text is None
        assert len(view.attachments) == 1

    async def test_khong_cau_hinh_url_cong_khai_van_luu_anh(self) -> None:
        """Thiếu ``ATTACHMENT_PUBLIC_BASE_URL``: ảnh vẫn vào lịch sử, chỉ không gửi kèm."""
        bc = _BoiCanh()  # public_url=None
        await bc.seed()

        view = await bc.use_case.execute(
            _nhan_vien(),
            bc.conversation.id,
            MessageContent(
                text="x",
                attachments=(AttachmentRef(kind=AttachmentKind.IMAGE, content_type="image/png"),),
            ),
            raw_attachments=[b"anh"],
        )

        assert bc.store.saved == [b"anh"]
        assert len(view.attachments) == 1

    async def test_lech_so_tep_va_tham_chieu_bi_chan(self) -> None:
        """Chặn sớm thay vì để ``zip(strict=True)`` nổ giữa chừng sau khi đã gửi."""
        bc = self._boi_canh_co_url()
        await bc.seed()

        with pytest.raises(ValueError, match="không khớp"):
            await bc.use_case.execute(
                _nhan_vien(),
                bc.conversation.id,
                MessageContent(
                    text="x",
                    attachments=(
                        AttachmentRef(kind=AttachmentKind.IMAGE),
                        AttachmentRef(kind=AttachmentKind.IMAGE),
                    ),
                ),
                raw_attachments=[b"chi-mot-tep"],
            )

        assert bc.adapter.sent == []
