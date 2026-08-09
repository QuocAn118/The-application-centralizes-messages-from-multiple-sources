import hashlib
import hmac
import json

import httpx
import pytest

from src.modules.inbox.domain.value_objects.message_content import (
    AttachmentKind,
    AttachmentRef,
    MessageContent,
)
from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.channels.meta_adapter import MetaAdapter
from src.modules.inbox.infrastructure.channels.zalo_adapter import WebhookSignatureError

APP_SECRET = "meta_app_secret"


def _adapter(platform=Platform.FACEBOOK, client_factory=None) -> MetaAdapter:
    return MetaAdapter(platform, APP_SECRET, client_factory=client_factory)


def _ky(raw: bytes) -> str:
    return "sha256=" + hmac.new(APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()


def _payload(mid: str = "m1", text: str = "xin chao", obj: str = "page") -> bytes:
    return json.dumps(
        {
            "object": obj,
            "entry": [
                {
                    "id": "page_1",
                    "messaging": [
                        {
                            "sender": {"id": "psid_1"},
                            "recipient": {"id": "page_1"},
                            "message": {"mid": mid, "text": text},
                        }
                    ],
                }
            ],
        }
    ).encode()


class TestVerifyChuKy:
    def test_chu_ky_dung(self) -> None:
        raw = _payload()
        events = _adapter().parse_webhook(raw, {"X-Hub-Signature-256": _ky(raw)})
        assert len(events) == 1
        assert events[0].external_message_id == "m1"

    def test_chu_ky_sai_bi_tu_choi(self) -> None:
        raw = _payload()
        with pytest.raises(WebhookSignatureError):
            _adapter().parse_webhook(raw, {"X-Hub-Signature-256": "sha256=deadbeef"})

    def test_thieu_header_bi_tu_choi(self) -> None:
        raw = _payload()
        with pytest.raises(WebhookSignatureError):
            _adapter().parse_webhook(raw, {})

    def test_body_bi_sua_bi_tu_choi(self) -> None:
        raw = _payload()
        chu_ky = _ky(raw)
        with pytest.raises(WebhookSignatureError):
            _adapter().parse_webhook(_payload(text="sua"), {"X-Hub-Signature-256": chu_ky})


class TestChuanHoa:
    def test_gan_dung_platform(self) -> None:
        raw = _payload()
        ev = _adapter(Platform.INSTAGRAM).parse_webhook(raw, {"X-Hub-Signature-256": _ky(raw)})[0]
        assert ev.platform is Platform.INSTAGRAM

    def test_recipient_la_external_channel_id(self) -> None:
        raw = _payload()
        ev = _adapter().parse_webhook(raw, {"X-Hub-Signature-256": _ky(raw)})[0]
        assert ev.external_channel_id == "page_1"
        assert ev.external_customer_id == "psid_1"

    def test_nhieu_entry_nhieu_messaging(self) -> None:
        raw = json.dumps(
            {
                "object": "page",
                "entry": [
                    {
                        "messaging": [
                            {
                                "sender": {"id": "u1"},
                                "recipient": {"id": "p1"},
                                "message": {"mid": "a", "text": "1"},
                            },
                            {
                                "sender": {"id": "u2"},
                                "recipient": {"id": "p1"},
                                "message": {"mid": "b", "text": "2"},
                            },
                        ]
                    }
                ],
            }
        ).encode()
        events = _adapter().parse_webhook(raw, {"X-Hub-Signature-256": _ky(raw)})
        assert {e.external_message_id for e in events} == {"a", "b"}

    def test_echo_bi_bo_qua(self) -> None:
        raw = json.dumps(
            {
                "object": "page",
                "entry": [
                    {
                        "messaging": [
                            {
                                "sender": {"id": "p1"},
                                "recipient": {"id": "u1"},
                                "message": {"mid": "e", "text": "echo", "is_echo": True},
                            }
                        ]
                    }
                ],
            }
        ).encode()
        assert _adapter().parse_webhook(raw, {"X-Hub-Signature-256": _ky(raw)}) == []

    def test_su_kien_delivery_bi_bo_qua(self) -> None:
        raw = json.dumps(
            {
                "object": "page",
                "entry": [{"messaging": [{"sender": {"id": "u1"}, "delivery": {"mids": ["x"]}}]}],
            }
        ).encode()
        assert _adapter().parse_webhook(raw, {"X-Hub-Signature-256": _ky(raw)}) == []

    def test_tin_co_anh(self) -> None:
        raw = json.dumps(
            {
                "object": "page",
                "entry": [
                    {
                        "messaging": [
                            {
                                "sender": {"id": "u1"},
                                "recipient": {"id": "p1"},
                                "message": {
                                    "mid": "img",
                                    "attachments": [
                                        {"type": "image", "payload": {"url": "https://cdn/a.jpg"}}
                                    ],
                                },
                            }
                        ]
                    }
                ],
            }
        ).encode()
        ev = _adapter().parse_webhook(raw, {"X-Hub-Signature-256": _ky(raw)})[0]
        assert ev.content.attachments[0].kind is AttachmentKind.IMAGE


class TestGuiTin:
    async def test_gui_tin_qua_graph_api(self) -> None:
        ghi_lai = {}

        def handler(request: httpx.Request) -> httpx.Response:
            ghi_lai["token"] = request.url.params.get("access_token")
            ghi_lai["body"] = json.loads(request.content)
            return httpx.Response(200, json={"message_id": "mid_9"})

        transport = httpx.MockTransport(handler)
        adapter = _adapter(client_factory=lambda: httpx.AsyncClient(transport=transport))

        ref = await adapter.send_message("tok", "psid_1", MessageContent(text="chao"))

        assert ref.external_message_id == "mid_9"
        assert ghi_lai["token"] == "tok"
        assert ghi_lai["body"]["recipient"]["id"] == "psid_1"


class TestKhoiTao:
    def test_khong_nhan_platform_zalo(self) -> None:
        with pytest.raises(ValueError):
            MetaAdapter(Platform.ZALO, APP_SECRET)


class TestTaiMedia:
    async def test_tai_media(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"file-bytes")

        transport = httpx.MockTransport(handler)
        adapter = _adapter(client_factory=lambda: httpx.AsyncClient(transport=transport))
        data = await adapter.download_attachment(
            AttachmentRef(kind=AttachmentKind.FILE, url="https://cdn/f.pdf")
        )
        assert data == b"file-bytes"


class TestGuiKemAnh:
    """Meta không cho text và ảnh trong CÙNG một tin, nên phải tách hai lời gọi."""

    async def test_text_va_anh_tach_thanh_hai_tin_dung_thu_tu(self) -> None:
        cac_body: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            cac_body.append(json.loads(request.content))
            return httpx.Response(200, json={"message_id": f"mid_{len(cac_body)}"})

        transport = httpx.MockTransport(handler)
        adapter = _adapter(client_factory=lambda: httpx.AsyncClient(transport=transport))

        ref = await adapter.send_message(
            "tok",
            "psid_1",
            MessageContent(
                text="anh day",
                attachments=(
                    AttachmentRef(kind=AttachmentKind.IMAGE, url="https://vidu.test/a.png"),
                ),
            ),
        )

        assert len(cac_body) == 2
        # Text đi trước để giữ đúng thứ tự người dùng gõ.
        assert cac_body[0]["message"]["text"] == "anh day"
        anh = cac_body[1]["message"]["attachment"]
        assert anh["type"] == "image"
        assert anh["payload"]["url"] == "https://vidu.test/a.png"
        # Trả mã của tin CUỐI.
        assert ref.external_message_id == "mid_2"

    async def test_chi_co_anh_thi_mot_loi_goi(self) -> None:
        cac_body: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            cac_body.append(json.loads(request.content))
            return httpx.Response(200, json={"message_id": "mid_1"})

        transport = httpx.MockTransport(handler)
        adapter = _adapter(client_factory=lambda: httpx.AsyncClient(transport=transport))

        await adapter.send_message(
            "tok",
            "psid_1",
            MessageContent(
                attachments=(
                    AttachmentRef(kind=AttachmentKind.IMAGE, url="https://vidu.test/a.png"),
                ),
            ),
        )

        assert len(cac_body) == 1
        assert "attachment" in cac_body[0]["message"]
