"""Adapter Meta — implementation ``IChannelAdapter`` cho Facebook và Instagram.

Facebook Page và Instagram dùng chung cơ chế ký webhook (X-Hub-Signature-256)
và Graph API, nhưng là hai ``Platform`` riêng (spec §11). Nên cùng một class,
tham số hoá bằng ``platform``, được dựng hai lần trong registry.
"""

import hashlib
import hmac
import json
from collections.abc import Callable
from typing import Any

import httpx

from src.modules.inbox.domain.ports import InboundEvent, SentMessageRef
from src.modules.inbox.domain.value_objects.message_content import (
    AttachmentKind,
    AttachmentRef,
    MessageContent,
)
from src.modules.inbox.domain.value_objects.platform import Platform

# Từ webhook Meta không ký, dùng lại lỗi chung của Zalo adapter để router bắt 403.
from src.modules.inbox.infrastructure.channels.zalo_adapter import WebhookSignatureError

_GRAPH_SEND_URL = "https://graph.facebook.com/v21.0/me/messages"
_SIGNATURE_HEADER = "x-hub-signature-256"

# Meta gói ảnh/video/audio là "image"/"video"/"audio"; còn lại coi là file.
_IMAGE_TYPES = {"image"}


class MetaAdapter:
    """Bộ chuyển đổi giữa một nền tảng Meta (FB hoặc IG) và mô hình inbox chung.

    ``app_secret`` là bí mật cấp *ứng dụng* để verify chữ ký; ``send_message``
    dùng page/IG access token (credential cấp kênh) do use case giải mã đưa vào.
    """

    def __init__(
        self,
        platform: Platform,
        app_secret: str,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        if platform not in (Platform.FACEBOOK, Platform.INSTAGRAM):
            raise ValueError("MetaAdapter chỉ phục vụ FACEBOOK hoặc INSTAGRAM.")
        self._platform = platform
        self._app_secret = app_secret
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=30.0))

    @property
    def platform(self) -> Platform:
        return self._platform

    # -- Webhook -------------------------------------------------------------

    def parse_webhook(self, raw_body: bytes, headers: dict[str, str]) -> list[InboundEvent]:
        self._xac_minh_chu_ky(raw_body, headers)
        payload = json.loads(raw_body)
        su_kien: list[InboundEvent] = []
        for entry in payload.get("entry", []):
            for messaging in entry.get("messaging", []):
                ev = self._chuan_hoa(messaging)
                if ev is not None:
                    su_kien.append(ev)
        return su_kien

    def _xac_minh_chu_ky(self, raw_body: bytes, headers: dict[str, str]) -> None:
        """sig = 'sha256=' + HMAC-SHA256(app_secret, raw_body).

        Ký trên body thô (không serialize lại). So sánh hằng thời gian.
        """
        header_chuan = {k.lower(): v for k, v in headers.items()}
        chu_ky_nhan = header_chuan.get(_SIGNATURE_HEADER, "")
        prefix, _, sig_nhan = chu_ky_nhan.partition("=")
        if prefix != "sha256" or not sig_nhan:
            raise WebhookSignatureError

        sig_dung = hmac.new(self._app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_dung, sig_nhan):
            raise WebhookSignatureError

    def _chuan_hoa(self, messaging: dict[str, Any]) -> InboundEvent | None:
        message = messaging.get("message")
        if not message or message.get("is_echo"):
            # Bỏ qua sự kiện không phải tin (delivery, read) và echo tin mình gửi.
            return None

        page_or_ig_id = str(messaging.get("recipient", {}).get("id", ""))
        sender_id = str(messaging.get("sender", {}).get("id", ""))
        message_id = str(message.get("mid", ""))
        if not page_or_ig_id or not sender_id or not message_id:
            return None

        text = message.get("text") or None
        attachments = self._chuan_hoa_dinh_kem(message.get("attachments", []))
        if text is None and not attachments:
            return None

        return InboundEvent(
            platform=self._platform,
            external_channel_id=page_or_ig_id,
            external_customer_id=sender_id,
            external_message_id=message_id,
            content=MessageContent(text=text, attachments=tuple(attachments)),
            customer_display_name=None,
        )

    @staticmethod
    def _chuan_hoa_dinh_kem(raw: list[dict[str, Any]]) -> list[AttachmentRef]:
        refs: list[AttachmentRef] = []
        for item in raw:
            loai = item.get("type", "")
            url = item.get("payload", {}).get("url")
            if not url:
                continue
            kind = AttachmentKind.IMAGE if loai in _IMAGE_TYPES else AttachmentKind.FILE
            refs.append(AttachmentRef(kind=kind, url=url))
        return refs

    # -- Gửi tin -------------------------------------------------------------

    async def send_message(
        self,
        encrypted_credential: str,
        external_customer_id: str,
        content: MessageContent,
    ) -> SentMessageRef:
        """Gửi tin qua Graph API. ``encrypted_credential`` là access token đã giải mã."""
        body = {
            "recipient": {"id": external_customer_id},
            "message": {"text": content.text or ""},
        }
        async with self._client_factory() as client:
            resp = await client.post(
                _GRAPH_SEND_URL,
                params={"access_token": encrypted_credential},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        message_id = data.get("message_id")
        return SentMessageRef(external_message_id=str(message_id) if message_id else None)

    # -- Tải media -----------------------------------------------------------

    async def download_attachment(self, ref: AttachmentRef) -> bytes:
        async with self._client_factory() as client:
            resp = await client.get(ref.url)
            resp.raise_for_status()
            return resp.content
