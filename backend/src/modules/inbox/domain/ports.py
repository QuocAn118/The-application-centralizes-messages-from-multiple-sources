"""Cổng (port) mà tầng application của inbox phụ thuộc.

Mọi thứ ở đây là interface: implementation nằm ở tầng infrastructure. Nhờ vậy
domain và use case không biết Zalo, Meta, đĩa, hay identity tồn tại — chúng chỉ
biết các hợp đồng này.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.inbox.domain.value_objects.message_content import (
    AttachmentRef,
    MessageContent,
)
from src.modules.inbox.domain.value_objects.platform import Platform


@dataclass(frozen=True)
class InboundEvent:
    """Một tin đến đã được adapter chuẩn hoá khỏi định dạng riêng của nền tảng.

    ``external_channel_id`` để tra ra kênh nào; ``external_customer_id`` để tra
    hoặc tạo khách; ``external_message_id`` là chốt idempotency.
    """

    platform: Platform
    external_channel_id: str
    external_customer_id: str
    external_message_id: str
    content: MessageContent
    customer_display_name: str | None = None


@dataclass(frozen=True)
class SentMessageRef:
    """Kết quả gửi tin đi: mã tin do nền tảng cấp (nếu có)."""

    external_message_id: str | None = None


@dataclass(frozen=True)
class ClosedConversation:
    """Payload phát cho các hook ``post_close`` khi một hội thoại vừa đóng.

    Trung lập, đủ để hạ nguồn (assignment #3 kéo hàng đợi theo ``department_id``;
    analytics #5 cộng rollup theo ``assigned_user_id``/``closed_at``) mà không phải
    tự đọc lại hội thoại. Các module hạ nguồn KHÔNG import lẫn nhau — chỉ cùng phụ
    thuộc kiểu này của inbox.
    """

    conversation_id: UUID
    department_id: UUID | None
    assigned_user_id: UUID | None
    closed_at: datetime


class IChannelAdapter(Protocol):
    """Bộ chuyển đổi giữa một nền tảng và mô hình chung của inbox.

    Mỗi nền tảng một implementation. Thêm nền tảng mới = thêm một adapter, không
    đụng domain hay use case.
    """

    @property
    def platform(self) -> Platform: ...

    def parse_webhook(self, raw_body: bytes, headers: dict[str, str]) -> list[InboundEvent]:
        """Xác minh chữ ký rồi chuẩn hoá payload webhook thành sự kiện miền.

        Ném lỗi nếu chữ ký sai — tuyệt đối không xử lý payload chưa xác minh.
        """
        ...

    async def send_message(
        self,
        access_token: str,
        external_customer_id: str,
        content: MessageContent,
    ) -> SentMessageRef:
        """Gửi một tin tới khách qua nền tảng.

        ``access_token`` là token **đã giải mã** (use case giải mã trước khi gọi);
        adapter không bao giờ thấy bản mã hoá.
        """
        ...

    async def download_attachment(self, ref: AttachmentRef) -> bytes:
        """Tải nội dung tệp đính kèm từ URL tạm của nền tảng."""
        ...


class IChannelAdapterRegistry(Protocol):
    """Tra adapter theo nền tảng."""

    def for_platform(self, platform: Platform) -> IChannelAdapter: ...


class ICredentialCipher(Protocol):
    """Mã hoá/giải mã credential của kênh.

    DB chỉ lưu bản mã hoá; token thô chỉ tồn tại trong bộ nhớ khi cần gọi API.
    """

    def encrypt(self, plaintext: str) -> str: ...

    def decrypt(self, ciphertext: str) -> str: ...


@dataclass(frozen=True)
class StoredAttachment:
    """Vị trí và siêu dữ liệu của một tệp đã lưu."""

    stored_path: str
    content_type: str | None = None
    size: int | None = None


class IAttachmentStore(Protocol):
    """Lưu và phục vụ lại tệp đính kèm.

    Implementation dev lưu đĩa local; đổi sang object storage sau không đụng
    use case.
    """

    async def save(
        self, data: bytes, suggested_name: str, content_type: str | None
    ) -> StoredAttachment: ...


@dataclass(frozen=True)
class AgentInfo:
    """Thông tin tối thiểu về một nhân viên, lấy từ module identity."""

    user_id: UUID
    department_id: UUID | None
    role: str
    is_active: bool


class IWorkforceDirectory(Protocol):
    """Hỏi module identity gián tiếp, không import identity vào inbox.

    Chỉ implementation ở infrastructure mới biết identity tồn tại. Đây là ranh
    giới giữ hai module độc lập.
    """

    async def get_agent(self, user_id: UUID) -> AgentInfo | None: ...

    async def department_exists_active(self, department_id: UUID) -> bool: ...


class IRealtimeNotifier(Protocol):
    """Đẩy tín hiệu 'có thay đổi' tới các client đang xem phạm vi liên quan.

    Chỉ gửi tín hiệu (conversation_id + loại thay đổi), không gửi nội dung tin —
    client tự gọi REST để lấy.
    """

    async def notify_conversation_changed(
        self,
        conversation_id: UUID,
        department_id: UUID | None,
        change: str,
    ) -> None: ...


# Loại thay đổi realtime, để router và notifier dùng chung một tên.
CHANGE_NEW_MESSAGE = "new_message"
CHANGE_STATUS = "status_changed"
