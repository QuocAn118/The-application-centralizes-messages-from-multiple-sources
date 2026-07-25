import hashlib
import json

import httpx
import pytest

from src.modules.inbox.domain.value_objects.message_content import (
    AttachmentKind,
    AttachmentRef,
    MessageContent,
)
from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.channels.zalo_adapter import (
    WebhookSignatureError,
    ZaloAdapter,
)

APP_ID = "app_123"
OA_SECRET = "oa_secret_xyz"


def _adapter(client_factory=None) -> ZaloAdapter:
    return ZaloAdapter(APP_ID, OA_SECRET, client_factory=client_factory)


def _ky(raw: bytes) -> str:
    payload = json.loads(raw)
    timestamp = str(payload["timestamp"])
    chuoi = APP_ID.encode() + raw + timestamp.encode() + OA_SECRET.encode()
    return "mac=" + hashlib.sha256(chuoi).hexdigest()


def _payload_tin_text(msg_id: str = "m1", text: str = "xin chao") -> bytes:
    return json.dumps(
        {
            "app_id": APP_ID,
            "oa_id": "oa_999",
            "timestamp": "1690000000000",
            "event_name": "user_send_text",
            "sender": {"id": "user_abc"},
            "message": {"msg_id": msg_id, "text": text},
        }
    ).encode()


class TestVerifyChuKy:
    def test_chu_ky_dung_thi_parse_duoc(self) -> None:
        raw = _payload_tin_text()
        events = _adapter().parse_webhook(raw, {"X-ZEvent-Signature": _ky(raw)})

        assert len(events) == 1
        assert events[0].external_message_id == "m1"

    def test_chu_ky_sai_bi_tu_choi(self) -> None:
        raw = _payload_tin_text()

        with pytest.raises(WebhookSignatureError):
            _adapter().parse_webhook(raw, {"X-ZEvent-Signature": "mac=deadbeef"})

    def test_thieu_header_chu_ky_bi_tu_choi(self) -> None:
        raw = _payload_tin_text()

        with pytest.raises(WebhookSignatureError):
            _adapter().parse_webhook(raw, {})

    def test_body_bi_sua_sau_khi_ky_bi_tu_choi(self) -> None:
        raw = _payload_tin_text()
        chu_ky = _ky(raw)
        raw_gia = _payload_tin_text(text="noi dung da bi sua")

        with pytest.raises(WebhookSignatureError):
            _adapter().parse_webhook(raw_gia, {"X-ZEvent-Signature": chu_ky})


class TestChuanHoa:
    def test_tin_text_thanh_inbound_event(self) -> None:
        raw = _payload_tin_text(msg_id="mm", text="hello")
        ev = _adapter().parse_webhook(raw, {"X-ZEvent-Signature": _ky(raw)})[0]

        assert ev.platform is Platform.ZALO
        assert ev.external_channel_id == "oa_999"
        assert ev.external_customer_id == "user_abc"
        assert ev.content.text == "hello"

    def test_tin_co_anh(self) -> None:
        raw = json.dumps(
            {
                "app_id": APP_ID,
                "oa_id": "oa_1",
                "timestamp": "1690000000001",
                "event_name": "user_send_image",
                "sender": {"id": "u1"},
                "message": {
                    "msg_id": "img1",
                    "attachments": [
                        {"type": "image", "payload": {"url": "https://cdn.zalo/a.jpg"}}
                    ],
                },
            }
        ).encode()

        ev = _adapter().parse_webhook(raw, {"X-ZEvent-Signature": _ky(raw)})[0]

        assert len(ev.content.attachments) == 1
        assert ev.content.attachments[0].kind is AttachmentKind.IMAGE
        assert ev.content.attachments[0].url == "https://cdn.zalo/a.jpg"

    def test_su_kien_khong_phai_tin_den_bi_bo_qua(self) -> None:
        raw = json.dumps(
            {
                "app_id": APP_ID,
                "oa_id": "oa_1",
                "timestamp": "1690000000002",
                "event_name": "follow",
                "follower": {"id": "u1"},
            }
        ).encode()

        events = _adapter().parse_webhook(raw, {"X-ZEvent-Signature": _ky(raw)})
        assert events == []


class TestGuiTin:
    async def test_gui_tin_goi_dung_endpoint_va_token(self) -> None:
        ghi_lai = {}

        def handler(request: httpx.Request) -> httpx.Response:
            ghi_lai["url"] = str(request.url)
            ghi_lai["token"] = request.headers.get("access_token")
            ghi_lai["body"] = json.loads(request.content)
            return httpx.Response(200, json={"data": {"message_id": "sent_9"}})

        transport = httpx.MockTransport(handler)
        adapter = _adapter(client_factory=lambda: httpx.AsyncClient(transport=transport))

        ref = await adapter.send_message("token_giai_ma", "user_abc", MessageContent(text="chao"))

        assert ref.external_message_id == "sent_9"
        assert ghi_lai["token"] == "token_giai_ma"
        assert ghi_lai["body"]["recipient"]["user_id"] == "user_abc"
        assert ghi_lai["body"]["message"]["text"] == "chao"


class TestTaiMedia:
    async def test_tai_media_tra_ve_bytes(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"anh-that")

        transport = httpx.MockTransport(handler)
        adapter = _adapter(client_factory=lambda: httpx.AsyncClient(transport=transport))

        data = await adapter.download_attachment(
            AttachmentRef(kind=AttachmentKind.IMAGE, url="https://cdn/a.jpg")
        )
        assert data == b"anh-that"
