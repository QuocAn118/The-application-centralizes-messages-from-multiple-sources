import json

import httpx
import pytest

from src.modules.inbox.domain.value_objects.message_content import (
    AttachmentKind,
    AttachmentRef,
    MessageContent,
)
from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.channels.errors import WebhookSignatureError
from src.modules.inbox.infrastructure.channels.telegram_adapter import TelegramAdapter

BOT_TOKEN = "123456789:AAHtestTokenGiaLapChoUnitTest"
BOT_ID = "123456789"
SECRET = "secret_webhook_rat_dai_va_ngau_nhien"


def _adapter(
    bot_token: str = BOT_TOKEN,
    secret: str = SECRET,
    client_factory=None,  # type: ignore[no-untyped-def]
) -> TelegramAdapter:
    return TelegramAdapter(bot_token, secret, client_factory=client_factory)


def _header(secret: str = SECRET) -> dict[str, str]:
    return {"X-Telegram-Bot-Api-Secret-Token": secret}


def _update(
    chat_id: int = 555,
    message_id: int = 7,
    text: str | None = "xin chao",
    **them: object,
) -> bytes:
    message: dict[str, object] = {
        "message_id": message_id,
        "chat": {"id": chat_id, "type": "private"},
        "from": {"id": chat_id, "first_name": "Lan", "last_name": "Nguyen"},
    }
    if text is not None:
        message["text"] = text
    message.update(them)
    return json.dumps({"update_id": 1, "message": message}).encode()


class TestXacMinhSecret:
    def test_secret_dung_thi_nhan(self) -> None:
        events = _adapter().parse_webhook(_update(), _header())
        assert len(events) == 1
        assert events[0].external_message_id == "555:7"

    def test_secret_sai_bi_tu_choi(self) -> None:
        with pytest.raises(WebhookSignatureError):
            _adapter().parse_webhook(_update(), _header("sai_secret"))

    def test_thieu_header_bi_tu_choi(self) -> None:
        with pytest.raises(WebhookSignatureError):
            _adapter().parse_webhook(_update(), {})

    def test_secret_cau_hinh_rong_thi_tu_choi_tat_ca(self) -> None:
        # Rỗng = từ chối hết, KHÔNG phải bỏ qua kiểm tra: webhook công khai
        # không xác thực là lỗ hổng.
        adapter = _adapter(secret="")
        with pytest.raises(WebhookSignatureError):
            adapter.parse_webhook(_update(), _header(""))

    def test_header_khong_phan_biet_hoa_thuong(self) -> None:
        events = _adapter().parse_webhook(_update(), {"x-telegram-bot-api-secret-token": SECRET})
        assert len(events) == 1

    def test_secret_dung_tien_to_van_bi_tu_choi(self) -> None:
        # So khớp phải là bằng tuyệt đối, không phải startswith.
        with pytest.raises(WebhookSignatureError):
            _adapter().parse_webhook(_update(), _header(SECRET[:-1]))


class TestChuanHoa:
    def test_gan_dung_platform_va_kenh_la_bot_id(self) -> None:
        ev = _adapter().parse_webhook(_update(), _header())[0]
        assert ev.platform is Platform.TELEGRAM
        # Kênh là BOT, không phải chat — nếu lấy chat.id thì mỗi khách thành một kênh.
        assert ev.external_channel_id == BOT_ID
        assert ev.external_customer_id == "555"

    def test_lay_text_va_ten_khach(self) -> None:
        ev = _adapter().parse_webhook(_update(), _header())[0]
        assert ev.content.text == "xin chao"
        assert ev.customer_display_name == "Lan Nguyen"

    def test_ten_khach_lui_ve_username_khi_thieu_ho_ten(self) -> None:
        raw = json.dumps(
            {
                "message": {
                    "message_id": 1,
                    "chat": {"id": 9, "type": "private"},
                    "from": {"id": 9, "username": "lan_nguyen"},
                    "text": "hi",
                }
            }
        ).encode()
        ev = _adapter().parse_webhook(raw, _header())[0]
        assert ev.customer_display_name == "lan_nguyen"

    def test_message_id_ghep_chat_id_de_khong_trung_giua_hai_khach(self) -> None:
        # Đây là bảo vệ quan trọng nhất của việc chuẩn hoá: message_id của
        # Telegram chỉ duy nhất trong MỘT chat.
        a = _adapter().parse_webhook(_update(chat_id=111, message_id=5), _header())[0]
        b = _adapter().parse_webhook(_update(chat_id=222, message_id=5), _header())[0]
        assert a.external_message_id != b.external_message_id
        assert a.external_message_id == "111:5"
        assert b.external_message_id == "222:5"

    def test_anh_lay_ban_lon_nhat(self) -> None:
        raw = _update(
            text=None,
            photo=[
                {"file_id": "nho", "width": 90},
                {"file_id": "vua", "width": 320},
                {"file_id": "lon", "width": 1280},
            ],
        )
        ev = _adapter().parse_webhook(raw, _header())[0]
        assert len(ev.content.attachments) == 1
        dinh_kem = ev.content.attachments[0]
        assert dinh_kem.kind is AttachmentKind.IMAGE
        # url mang file_id, không phải URL thật.
        assert dinh_kem.url == "lon"

    def test_anh_kem_chu_thich_lay_caption_lam_text(self) -> None:
        raw = _update(text=None, photo=[{"file_id": "f1"}], caption="anh san pham")
        ev = _adapter().parse_webhook(raw, _header())[0]
        assert ev.content.text == "anh san pham"
        assert len(ev.content.attachments) == 1

    def test_sticker_bi_bo_qua_hop_le(self) -> None:
        raw = _update(text=None, sticker={"file_id": "sticker_1"})
        assert _adapter().parse_webhook(raw, _header()) == []

    def test_update_khong_phai_tin_nhan_bi_bo_qua(self) -> None:
        raw = json.dumps({"update_id": 2, "callback_query": {"id": "cb1"}}).encode()
        assert _adapter().parse_webhook(raw, _header()) == []

    def test_tin_trong_nhom_bi_bo_qua(self) -> None:
        raw = json.dumps(
            {
                "message": {
                    "message_id": 1,
                    "chat": {"id": -100, "type": "group"},
                    "text": "hi",
                }
            }
        ).encode()
        assert _adapter().parse_webhook(raw, _header()) == []

    def test_thieu_chat_id_bi_bo_qua(self) -> None:
        raw = json.dumps({"message": {"message_id": 1, "text": "hi"}}).encode()
        assert _adapter().parse_webhook(raw, _header()) == []


class TestGuiTin:
    async def test_gui_text_qua_send_message(self) -> None:
        ghi_lai: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            ghi_lai["url"] = str(request.url)
            ghi_lai["body"] = json.loads(request.content)
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

        transport = httpx.MockTransport(handler)
        adapter = _adapter(client_factory=lambda: httpx.AsyncClient(transport=transport))

        ref = await adapter.send_message("tok123", "555", MessageContent(text="chao ban"))

        assert ref.external_message_id == "42"
        assert ghi_lai["url"] == "https://api.telegram.org/bottok123/sendMessage"
        assert ghi_lai["body"] == {"chat_id": "555", "text": "chao ban"}

    async def test_gui_anh_qua_send_photo_kem_caption(self) -> None:
        ghi_lai: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            ghi_lai["url"] = str(request.url)
            ghi_lai["body"] = json.loads(request.content)
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 43}})

        transport = httpx.MockTransport(handler)
        adapter = _adapter(client_factory=lambda: httpx.AsyncClient(transport=transport))

        noi_dung = MessageContent(
            text="anh day",
            attachments=(AttachmentRef(kind=AttachmentKind.IMAGE, url="https://cdn/a.jpg"),),
        )
        ref = await adapter.send_message("tok123", "555", noi_dung)

        assert ref.external_message_id == "43"
        assert ghi_lai["url"] == "https://api.telegram.org/bottok123/sendPhoto"
        # Text đi kèm ảnh trong CÙNG một tin qua caption.
        assert ghi_lai["body"] == {
            "chat_id": "555",
            "photo": "https://cdn/a.jpg",
            "caption": "anh day",
        }

    async def test_khong_co_message_id_tra_ve_none(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": True, "result": {}})

        transport = httpx.MockTransport(handler)
        adapter = _adapter(client_factory=lambda: httpx.AsyncClient(transport=transport))

        ref = await adapter.send_message("tok", "555", MessageContent(text="hi"))
        assert ref.external_message_id is None


class TestTaiAnh:
    async def test_tai_anh_hai_buoc_get_file_roi_tai_noi_dung(self) -> None:
        goi: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            goi.append(str(request.url))
            if "getFile" in str(request.url):
                return httpx.Response(
                    200, json={"ok": True, "result": {"file_path": "photos/f1.jpg"}}
                )
            return httpx.Response(200, content=b"noi-dung-anh")

        transport = httpx.MockTransport(handler)
        adapter = _adapter(client_factory=lambda: httpx.AsyncClient(transport=transport))

        data = await adapter.download_attachment(
            AttachmentRef(kind=AttachmentKind.IMAGE, url="file_id_1")
        )

        assert data == b"noi-dung-anh"
        assert len(goi) == 2
        assert "getFile" in goi[0] and "file_id_1" in goi[0]
        assert goi[1] == f"https://api.telegram.org/file/bot{BOT_TOKEN}/photos/f1.jpg"

    async def test_khong_co_file_path_thi_bao_loi(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": False, "result": {}})

        transport = httpx.MockTransport(handler)
        adapter = _adapter(client_factory=lambda: httpx.AsyncClient(transport=transport))

        with pytest.raises(ValueError):
            await adapter.download_attachment(AttachmentRef(kind=AttachmentKind.IMAGE, url="hong"))


class TestKhoiTao:
    def test_bot_id_lay_phan_truoc_dau_hai_cham(self) -> None:
        assert _adapter().bot_id == BOT_ID

    def test_token_rong_cho_bot_id_rong(self) -> None:
        # Không đoán bừa: bot id rỗng sẽ không khớp kênh nào, an toàn hơn.
        assert _adapter(bot_token="").bot_id == ""

    def test_platform_la_telegram(self) -> None:
        assert _adapter().platform is Platform.TELEGRAM
