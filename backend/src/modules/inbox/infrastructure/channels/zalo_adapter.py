"""Adapter Zalo OA — implementation của ``IChannelAdapter`` cho nền tảng Zalo.

Thêm nền tảng mới = thêm một adapter như file này, không đụng domain/use case
(RB-1). Adapter chịu trách nhiệm: xác minh chữ ký webhook (RB-3), chuẩn hoá
payload Zalo thành ``InboundEvent`` chung, gửi tin qua Open API, tải media về.
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
from src.modules.inbox.infrastructure.channels.errors import WebhookSignatureError

__all__ = ["WebhookSignatureError", "ZaloAdapter"]

_ZALO_SEND_URL = "https://openapi.zalo.me/v3.0/oa/message/cs"
_SIGNATURE_HEADER = "x-zevent-signature"


class ZaloAdapter:
    """Bộ chuyển đổi giữa Zalo OA và mô hình inbox chung.

    ``app_id`` và ``oa_secret_key`` là bí mật cấp *ứng dụng* (một Zalo app phục
    vụ nhiều OA), đọc từ ``.env`` khi dựng adapter — khác với credential *cấp
    kênh* (OA access token) truyền vào ``send_message``.
    """

    def __init__(
        self,
        app_id: str,
        oa_secret_key: str,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._app_id = app_id
        self._oa_secret_key = oa_secret_key
        # Cho test tiêm transport giả; production dùng client mặc định.
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=30.0))

    @property
    def platform(self) -> Platform:
        return Platform.ZALO

    # -- Webhook -------------------------------------------------------------

    def parse_webhook(self, raw_body: bytes, headers: dict[str, str]) -> list[InboundEvent]:
        self._xac_minh_chu_ky(raw_body, headers)
        payload = json.loads(raw_body)
        su_kien = self._chuan_hoa(payload)
        return [su_kien] if su_kien is not None else []

    def _xac_minh_chu_ky(self, raw_body: bytes, headers: dict[str, str]) -> None:
        """mac = sha256(app_id + raw_body + timestamp + oa_secret_key).

        ``timestamp`` lấy từ chính body (Zalo ký trên body thô, không được
        serialize lại). So sánh hằng thời gian để tránh timing attack.
        """
        header_chuan = {k.lower(): v for k, v in headers.items()}
        chu_ky_nhan = header_chuan.get(_SIGNATURE_HEADER, "")
        prefix, _, mac_nhan = chu_ky_nhan.partition("=")
        if prefix != "mac" or not mac_nhan:
            raise WebhookSignatureError

        try:
            timestamp = str(json.loads(raw_body)["timestamp"])
        except (KeyError, ValueError, TypeError) as exc:
            raise WebhookSignatureError from exc

        chuoi = self._app_id.encode() + raw_body + timestamp.encode() + self._oa_secret_key.encode()
        mac_dung = hashlib.sha256(chuoi).hexdigest()
        if not hmac.compare_digest(mac_dung, mac_nhan):
            raise WebhookSignatureError

    def _chuan_hoa(self, payload: dict[str, Any]) -> InboundEvent | None:
        """Chuẩn hoá một sự kiện Zalo thành ``InboundEvent``.

        Chỉ xử lý sự kiện tin đến từ người dùng (``user_send_*``); các sự kiện
        khác (follow, delivered...) bỏ qua ở #1.
        """
        event_name = payload.get("event_name", "")
        if not event_name.startswith("user_send_"):
            return None

        oa_id = str(payload.get("oa_id", ""))
        sender_id = str(payload.get("sender", {}).get("id", ""))
        message = payload.get("message", {})
        message_id = str(message.get("msg_id", ""))
        if not oa_id or not sender_id or not message_id:
            return None

        text = message.get("text") or None
        attachments = self._chuan_hoa_dinh_kem(message.get("attachments", []))
        if text is None and not attachments:
            return None

        return InboundEvent(
            platform=Platform.ZALO,
            external_channel_id=oa_id,
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
            payload = item.get("payload", {})
            url = payload.get("url") or payload.get("thumbnail")
            if not url:
                continue
            kind = AttachmentKind.IMAGE if loai == "image" else AttachmentKind.FILE
            refs.append(AttachmentRef(kind=kind, url=url))
        return refs

    # -- Gửi tin -------------------------------------------------------------

    async def send_message(
        self,
        access_token: str,
        external_customer_id: str,
        content: MessageContent,
    ) -> SentMessageRef:
        """Gửi tin qua Zalo Open API (token đã giải mã, use case lo việc đó).

        Dùng endpoint ``/message/cs`` (chăm sóc khách hàng): hợp lệ để trả lời
        trong cửa sổ tương tác sau tin cuối của khách — đúng luồng inbox #1. #1
        gửi phần text; media để iteration sau.
        """
        body = {
            "recipient": {"user_id": external_customer_id},
            "message": {"text": content.text or ""},
        }
        async with self._client_factory() as client:
            resp = await client.post(
                _ZALO_SEND_URL,
                headers={"access_token": access_token},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        message_id = data.get("data", {}).get("message_id")
        return SentMessageRef(external_message_id=str(message_id) if message_id else None)

    # -- Tải media -----------------------------------------------------------

    async def download_attachment(self, ref: AttachmentRef) -> bytes:
        # NỢ: URL media Zalo có thể cần access_token để tải (ảnh không public).
        # #1 tải trực tiếp; nếu gặp 401/403 thật thì truyền token vào đây.
        async with self._client_factory() as client:
            resp = await client.get(ref.url)
            resp.raise_for_status()
            return resp.content
