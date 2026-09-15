"""Adapter Telegram Bot API — implementation ``IChannelAdapter``.

Kênh thứ ba của #1, thêm để chạy được luồng đầu-cuối thật mà không cần giấy phép
kinh doanh (Zalo OA) hay tài khoản Meta Developer. Thêm nền tảng = thêm một file
như file này, không đụng domain/use case (RB-1).

Ba khác biệt so với Zalo/Meta, đều có lý do từ phía Telegram:

1. **Xác thực không dùng chữ ký.** Telegram không ký request. Thay vào đó nó gửi
   lại nguyên văn một secret do mình đặt lúc ``setWebhook``, ở header
   ``X-Telegram-Bot-Api-Secret-Token``. Nên ở đây là so khớp hằng thời gian,
   không phải HMAC.
2. **Ảnh không có URL trong webhook.** Webhook chỉ trả ``file_id``; muốn lấy
   bytes phải gọi ``getFile`` rồi mới tải. Xem ``download_attachment``.
3. **``message_id`` chỉ duy nhất trong một chat**, không duy nhất toàn cục — nên
   khoá idempotency phải ghép thêm ``chat_id``.
"""

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

__all__ = ["TelegramAdapter"]

_API_GOC = "https://api.telegram.org"
_SECRET_HEADER = "x-telegram-bot-api-secret-token"


class TelegramAdapter:
    """Bộ chuyển đổi giữa Telegram Bot API và mô hình inbox chung.

    ``webhook_secret`` là bí mật cấp *ứng dụng* (đặt lúc ``setWebhook``), đọc từ
    ``.env`` khi dựng adapter — khác với credential *cấp kênh* (bot token) mà use
    case giải mã rồi truyền vào ``send_message``.

    ``bot_token`` ở đây chỉ dùng để tải ảnh về (``download_attachment`` không
    nhận token qua tham số, khác ``send_message``). Với triển khai một-bot hiện
    tại, token này trùng credential của kênh.
    """

    def __init__(
        self,
        bot_token: str,
        webhook_secret: str,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._bot_token = bot_token
        self._webhook_secret = webhook_secret
        # Cho test tiêm transport giả; production dùng client mặc định.
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=30.0))

    @property
    def platform(self) -> Platform:
        return Platform.TELEGRAM

    @property
    def bot_id(self) -> str:
        """Phần số trước dấu hai chấm của bot token — định danh kênh.

        Một bot là *một kênh*, mỗi người chat với bot là *một khách* (song song
        với "một OA là một kênh" ở Zalo). Token rỗng/dị dạng trả chuỗi rỗng, khi
        đó sự kiện sẽ không khớp kênh nào — an toàn hơn là đoán bừa.
        """
        return self._bot_token.partition(":")[0]

    # -- Webhook -------------------------------------------------------------

    def parse_webhook(self, raw_body: bytes, headers: dict[str, str]) -> list[InboundEvent]:
        self._xac_minh_secret(headers)
        payload = json.loads(raw_body)
        su_kien = self._chuan_hoa(payload)
        return [su_kien] if su_kien is not None else []

    def _xac_minh_secret(self, headers: dict[str, str]) -> None:
        """So khớp ``X-Telegram-Bot-Api-Secret-Token`` hằng thời gian.

        Telegram KHÔNG ký body — secret chỉ chứng minh *người gọi* là Telegram,
        không chứng minh *body chưa bị sửa*. Vì vậy secret phải dài, ngẫu nhiên,
        và endpoint bắt buộc chạy HTTPS.

        Secret rỗng thì từ chối TẤT CẢ, chứ không phải bỏ qua kiểm tra: một
        webhook công khai không xác thực là lỗ hổng, còn cấu hình thiếu là lỗi
        người vận hành sẽ thấy ngay khi không tin nào vào được.
        """
        if not self._webhook_secret:
            raise WebhookSignatureError

        header_chuan = {k.lower(): v for k, v in headers.items()}
        nhan_duoc = header_chuan.get(_SECRET_HEADER, "")
        if not hmac.compare_digest(nhan_duoc, self._webhook_secret):
            raise WebhookSignatureError

    def _chuan_hoa(self, payload: dict[str, Any]) -> InboundEvent | None:
        """Chuẩn hoá một ``Update`` của Telegram thành ``InboundEvent``.

        Chỉ xử lý tin nhắn mới trong chat 1-1 (``message``). Các update khác
        (``edited_message``, ``callback_query``, tin trong nhóm/kênh...) bỏ qua
        hợp lệ ở bản này — trả ``None`` để router vẫn đáp 200, không phải lỗi.
        """
        message = payload.get("message")
        if not isinstance(message, dict):
            return None

        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        message_id = message.get("message_id")
        if not chat_id or message_id is None:
            return None

        # Chỉ nhận chat riêng: nhóm/kênh ngoài phạm vi (spec §8).
        if chat.get("type") not in (None, "private"):
            return None

        # Ảnh đi kèm chú thích thì text nằm ở ``caption``, không phải ``text``.
        text = message.get("text") or message.get("caption") or None
        attachments = self._chuan_hoa_dinh_kem(message)
        if text is None and not attachments:
            # Sticker, voice, video, document... chưa hỗ trợ: bỏ qua hợp lệ thay
            # vì tạo một tin rỗng (MessageContent sẽ ném lỗi nếu cố dựng).
            return None

        return InboundEvent(
            platform=Platform.TELEGRAM,
            external_channel_id=self.bot_id,
            external_customer_id=chat_id,
            # ``message_id`` chỉ duy nhất TRONG MỘT CHAT. Không ghép chat_id thì
            # tin của khách B sẽ bị idempotency coi là trùng tin của khách A và
            # bị nuốt mất — lỗi im lặng, mất dữ liệu thật.
            external_message_id=f"{chat_id}:{message_id}",
            content=MessageContent(text=text, attachments=tuple(attachments)),
            customer_display_name=self._ten_khach(message.get("from")),
        )

    @staticmethod
    def _ten_khach(nguoi_gui: dict[str, Any] | None) -> str | None:
        """Ghép tên hiển thị từ ``from``; không có họ tên thì lấy username."""
        if not isinstance(nguoi_gui, dict):
            return None
        phan = [nguoi_gui.get("first_name"), nguoi_gui.get("last_name")]
        ho_ten = " ".join(p for p in phan if p)
        return ho_ten or nguoi_gui.get("username") or None

    @staticmethod
    def _chuan_hoa_dinh_kem(message: dict[str, Any]) -> list[AttachmentRef]:
        """Lấy ảnh từ ``photo``.

        Telegram gửi nhiều bản cùng một ảnh theo kích thước TĂNG DẦN; bản cuối
        là bản lớn nhất, đó là bản ta lưu. ``url`` ở đây mang ``file_id`` chứ
        không phải URL thật — ``download_attachment`` sẽ đổi nó thành bytes.
        """
        photo = message.get("photo")
        if not isinstance(photo, list) or not photo:
            return []
        file_id = photo[-1].get("file_id")
        if not file_id:
            return []
        return [AttachmentRef(kind=AttachmentKind.IMAGE, url=str(file_id))]

    # -- Gửi tin -------------------------------------------------------------

    async def send_message(
        self,
        access_token: str,
        external_customer_id: str,
        content: MessageContent,
    ) -> SentMessageRef:
        """Gửi tin qua Bot API (token đã giải mã, use case lo việc đó).

        Ảnh gửi bằng ``sendPhoto`` với ``photo`` là URL công khai — Telegram TỰ
        TẢI ảnh từ URL ta cung cấp, nên URL đó phải truy cập được từ máy chủ
        Telegram (xem ``ATTACHMENT_PUBLIC_BASE_URL``), giống hệt Zalo/Meta.

        Có cả ảnh lẫn text thì dùng ``caption`` của ``sendPhoto`` để cả hai nằm
        trong MỘT tin — khác Meta (Graph API không cho gộp, phải tách hai tin).
        """
        anh = next(
            (a for a in content.attachments if a.kind is AttachmentKind.IMAGE and a.url),
            None,
        )
        if anh is not None:
            phuong_thuc = "sendPhoto"
            body: dict[str, Any] = {"chat_id": external_customer_id, "photo": anh.url}
            if content.text:
                body["caption"] = content.text
        else:
            phuong_thuc = "sendMessage"
            body = {"chat_id": external_customer_id, "text": content.text or ""}

        async with self._client_factory() as client:
            resp = await client.post(
                f"{_API_GOC}/bot{access_token}/{phuong_thuc}",
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        message_id = data.get("result", {}).get("message_id")
        return SentMessageRef(external_message_id=str(message_id) if message_id else None)

    # -- Tải media -----------------------------------------------------------

    async def download_attachment(self, ref: AttachmentRef) -> bytes:
        """Đổi ``file_id`` thành bytes — hai bước, theo thiết kế của Bot API.

        ``getFile`` trả ``file_path`` có hiệu lực khoảng một giờ; nội dung tải ở
        một đường dẫn khác (``/file/bot<token>/...``). Đây là lý do RB-4 tồn tại:
        phải tải về lưu lại, không thể trỏ thẳng vào Telegram mãi.
        """
        async with self._client_factory() as client:
            resp = await client.get(
                f"{_API_GOC}/bot{self._bot_token}/getFile",
                params={"file_id": ref.url},
            )
            resp.raise_for_status()
            file_path = resp.json().get("result", {}).get("file_path")
            if not file_path:
                raise ValueError("Telegram không trả file_path cho file_id này.")

            tai_ve = await client.get(f"{_API_GOC}/file/bot{self._bot_token}/{file_path}")
            tai_ve.raise_for_status()
            return tai_ve.content
