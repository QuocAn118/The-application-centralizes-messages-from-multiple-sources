from datetime import UTC, datetime

from src.modules.inbox.application.use_cases.ingest_inbound_message import (
    IngestInboundMessage,
)
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import ConversationStatus
from src.modules.inbox.domain.ports import CHANGE_NEW_MESSAGE, InboundEvent
from src.modules.inbox.domain.value_objects.message_content import (
    AttachmentKind,
    AttachmentRef,
    MessageContent,
)
from src.modules.inbox.domain.value_objects.platform import Platform
from src.shared.domain.identifiers import new_id
from tests.unit.inbox.fakes import (
    FakeAttachmentStore,
    FakeChannelRepository,
    FakeClock,
    FakeConversationRepository,
    FakeCustomerRepository,
    FakeMessageRepository,
    FakeRealtimeNotifier,
)

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)


async def _khong_tai(ref: AttachmentRef) -> bytes:
    """Hàm tải giả cho tin không đính kèm — không bao giờ được gọi."""
    raise AssertionError("Không nên tải khi không có đính kèm.")


def _tai_co_dinh(data: bytes):  # type: ignore[no-untyped-def]
    """Trả một hàm tải luôn trả cùng nội dung, đếm số lần gọi."""

    async def _tai(ref: AttachmentRef) -> bytes:
        _tai.so_lan += 1  # type: ignore[attr-defined]
        return data

    _tai.so_lan = 0  # type: ignore[attr-defined]
    return _tai


class _BoiCanh:
    def __init__(self, channel: Channel) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.channel_repo = FakeChannelRepository([channel])
        self.customer_repo = FakeCustomerRepository()
        self.conversation_repo = FakeConversationRepository()
        self.message_repo = FakeMessageRepository()
        self.store = FakeAttachmentStore()
        self.notifier = FakeRealtimeNotifier()
        self.channel = channel
        self.use_case = IngestInboundMessage(
            channel_repo=self.channel_repo,
            customer_repo=self.customer_repo,
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
            attachment_store=self.store,
            notifier=self.notifier,
            clock=self.clock,
        )


def _kenh(department_id=None) -> Channel:
    return Channel.connect(
        platform=Platform.ZALO,
        external_channel_id="oa_123",
        name="OA Test",
        department_id=department_id,
        encrypted_credential="enc::token",
        now=BAY_GIO,
    )


def _su_kien(
    external_message_id: str = "msg_1",
    text: str | None = "xin chao",
    attachments=(),
    ten: str | None = "Khach A",
) -> InboundEvent:
    return InboundEvent(
        platform=Platform.ZALO,
        external_channel_id="oa_123",
        external_customer_id="cust_9",
        external_message_id=external_message_id,
        content=MessageContent(text=text, attachments=tuple(attachments)),
        customer_display_name=ten,
    )


class TestTaoMoi:
    async def test_tin_moi_tao_khach_hoi_thoai_va_message(self) -> None:
        bc = _BoiCanh(_kenh())

        view = await bc.use_case.execute(_su_kien(), _khong_tai)

        assert view is not None
        assert view.text == "xin chao"
        assert len(bc.message_repo.messages) == 1
        # Có đúng một khách và một hội thoại được tạo.
        khach = await bc.customer_repo.get_by_external(bc.channel.id, "cust_9")
        assert khach is not None
        assert khach.display_name == "Khach A"

    async def test_kenh_khong_gan_phong_thi_hoi_thoai_cho_phan(self) -> None:
        bc = _BoiCanh(_kenh(department_id=None))

        await bc.use_case.execute(_su_kien(), _khong_tai)

        khach = await bc.customer_repo.get_by_external(bc.channel.id, "cust_9")
        assert khach is not None
        ht = await bc.conversation_repo.get_open_for(bc.channel.id, khach.id)
        assert ht is not None
        assert ht.status is ConversationStatus.CHO_PHAN

    async def test_kenh_gan_phong_thi_hoi_thoai_dang_mo(self) -> None:
        phong = new_id()
        bc = _BoiCanh(_kenh(department_id=phong))

        await bc.use_case.execute(_su_kien(), _khong_tai)

        khach = await bc.customer_repo.get_by_external(bc.channel.id, "cust_9")
        assert khach is not None
        ht = await bc.conversation_repo.get_open_for(bc.channel.id, khach.id)
        assert ht is not None
        assert ht.status is ConversationStatus.DANG_MO
        assert ht.department_id == phong

    async def test_gui_tin_hieu_realtime_co_tin_moi(self) -> None:
        bc = _BoiCanh(_kenh())

        await bc.use_case.execute(_su_kien(), _khong_tai)

        assert len(bc.notifier.signals) == 1
        _, _, loai = bc.notifier.signals[0]
        assert loai == CHANGE_NEW_MESSAGE


class TestIdempotency:
    async def test_event_trung_khong_tao_ban_trung(self) -> None:
        bc = _BoiCanh(_kenh())

        first = await bc.use_case.execute(_su_kien(external_message_id="dup"), _khong_tai)
        second = await bc.use_case.execute(_su_kien(external_message_id="dup"), _khong_tai)

        assert first is not None
        assert second is None
        assert len(bc.message_repo.messages) == 1
        assert len(bc.notifier.signals) == 1


class TestKenhKhongTonTai:
    async def test_webhook_toi_kenh_la_bi_bo_qua(self) -> None:
        bc = _BoiCanh(_kenh())
        su_kien_la = InboundEvent(
            platform=Platform.ZALO,
            external_channel_id="oa_khong_ton_tai",
            external_customer_id="cust_9",
            external_message_id="msg_x",
            content=MessageContent(text="hi"),
        )

        ket_qua = await bc.use_case.execute(su_kien_la, _khong_tai)

        assert ket_qua is None
        assert len(bc.message_repo.messages) == 0


class TestNoiTinVaoHoiThoaiCu:
    async def test_tin_thu_hai_noi_vao_hoi_thoai_dang_mo(self) -> None:
        bc = _BoiCanh(_kenh())

        await bc.use_case.execute(_su_kien(external_message_id="m1"), _khong_tai)
        await bc.use_case.execute(_su_kien(external_message_id="m2"), _khong_tai)

        khach = await bc.customer_repo.get_by_external(bc.channel.id, "cust_9")
        assert khach is not None
        # Chỉ một hội thoại; cả hai tin vào cùng chỗ.
        assert len(bc.message_repo.messages) == 2


class TestDinhKem:
    async def test_anh_duoc_tai_ve_va_luu(self) -> None:
        bc = _BoiCanh(_kenh())
        su_kien = _su_kien(
            text=None,
            attachments=[
                AttachmentRef(
                    kind=AttachmentKind.IMAGE,
                    url="https://cdn.zalo/anh.jpg",
                    content_type="image/jpeg",
                )
            ],
        )

        tai = _tai_co_dinh(b"noi-dung-anh")
        view = await bc.use_case.execute(su_kien, tai)

        assert view is not None
        assert len(view.attachments) == 1
        assert view.attachments[0].kind is AttachmentKind.IMAGE
        assert bc.store.saved == [b"noi-dung-anh"]
        assert tai.so_lan == 1  # type: ignore[attr-defined]

    async def test_event_trung_khong_tai_media(self) -> None:
        # Idempotency chặn TRƯỚC khi tải: webhook lặp lại không kéo tải media
        # (chống lãng phí + DoS). Hàm tải không được gọi ở lần trùng.
        bc = _BoiCanh(_kenh())
        su_kien = _su_kien(
            external_message_id="dup_img",
            text=None,
            attachments=[AttachmentRef(kind=AttachmentKind.IMAGE, url="https://cdn/1.jpg")],
        )

        tai = _tai_co_dinh(b"anh")
        await bc.use_case.execute(su_kien, tai)
        second = await bc.use_case.execute(su_kien, tai)

        assert second is None
        assert tai.so_lan == 1  # type: ignore[attr-defined]  # chỉ tải lần đầu
