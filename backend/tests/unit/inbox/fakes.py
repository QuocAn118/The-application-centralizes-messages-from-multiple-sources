"""Fake in-memory cho unit test use case của inbox.

Fake phản ánh hành vi thật của repository/adapter; khi hợp đồng đổi, fake sai
làm test đỏ — đúng thứ ta muốn. Mock thì không.
"""

from datetime import datetime
from uuid import UUID

from src.modules.inbox.domain.entities.attachment import Attachment
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import (
    Conversation,
    ConversationStatus,
)
from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.domain.entities.message import Message
from src.modules.inbox.domain.ports import (
    AgentInfo,
    InboundEvent,
    SentMessageRef,
    StoredAttachment,
)
from src.modules.inbox.domain.value_objects.message_content import (
    AttachmentRef,
    MessageContent,
)
from src.modules.inbox.domain.value_objects.platform import Platform


class FakeClock:
    """Đồng hồ cố định để test kiểm soát thời gian.

    ``tick`` cho phép nhích thời gian giữa các bước, ví dụ để phân biệt thời
    điểm tin đến với thời điểm trả lời.
    """

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        self._now = now


class FakeChannelRepository:
    def __init__(self, channels: list[Channel] | None = None) -> None:
        self._channels: dict[UUID, Channel] = {c.id: c for c in (channels or [])}

    async def get_by_id(self, channel_id: UUID) -> Channel | None:
        return self._channels.get(channel_id)

    async def get_by_external(self, platform: Platform, external_channel_id: str) -> Channel | None:
        for c in self._channels.values():
            if c.platform is platform and c.external_channel_id == external_channel_id:
                return c
        return None

    async def add(self, channel: Channel) -> None:
        self._channels[channel.id] = channel

    async def update(self, channel: Channel) -> None:
        self._channels[channel.id] = channel

    async def list_all(self, is_active: bool | None = None) -> list[Channel]:
        ket_qua = list(self._channels.values())
        if is_active is not None:
            ket_qua = [c for c in ket_qua if c.is_active is is_active]
        return sorted(ket_qua, key=lambda c: c.created_at)


class FakeCustomerRepository:
    def __init__(self) -> None:
        self._customers: dict[UUID, Customer] = {}

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        return self._customers.get(customer_id)

    async def get_by_external(self, channel_id: UUID, external_id: str) -> Customer | None:
        for c in self._customers.values():
            if c.channel_id == channel_id and c.external_id == external_id:
                return c
        return None

    async def add(self, customer: Customer) -> None:
        self._customers[customer.id] = customer

    async def update(self, customer: Customer) -> None:
        self._customers[customer.id] = customer


class FakeConversationRepository:
    def __init__(self) -> None:
        self._conversations: dict[UUID, Conversation] = {}
        # Tên khách để mô phỏng lọc theo ``q``; ở bản thật tên nằm ở bảng
        # ``customers`` và repository lọc bằng subquery.
        self.ten_khach: dict[UUID, str | None] = {}

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        return self._conversations.get(conversation_id)

    async def get_open_for(self, channel_id: UUID, customer_id: UUID) -> Conversation | None:
        for c in self._conversations.values():
            if (
                c.channel_id == channel_id
                and c.customer_id == customer_id
                and c.status is not ConversationStatus.DA_DONG
            ):
                return c
        return None

    async def add(self, conversation: Conversation) -> None:
        self._conversations[conversation.id] = conversation

    async def update(self, conversation: Conversation) -> None:
        self._conversations[conversation.id] = conversation

    def dat_ten_khach(self, customer_id: UUID, display_name: str | None) -> None:
        """Gắn tên khách để mô phỏng phần lọc theo ``q`` (thật ra ở bảng khác)."""
        self.ten_khach[customer_id] = display_name

    def _loc(
        self,
        department_ids: list[UUID] | None,
        include_awaiting: bool,
        status: ConversationStatus | None,
        q: str | None = None,
    ) -> list[Conversation]:
        tu_khoa = q.strip().lower() if q and q.strip() else None
        ket_qua = []
        for c in self._conversations.values():
            thuoc_pham_vi = department_ids is None or (
                c.department_id is not None and c.department_id in department_ids
            )
            la_cho_phan = c.status is ConversationStatus.CHO_PHAN
            trong_pham_vi = thuoc_pham_vi or (include_awaiting and la_cho_phan)
            khop_trang_thai = status is None or c.status is status

            if tu_khoa is None:
                khop_tim_kiem = True
            else:
                ten = self.ten_khach.get(c.customer_id)
                khop_tim_kiem = ten is not None and tu_khoa in ten.lower()

            if trong_pham_vi and khop_trang_thai and khop_tim_kiem:
                ket_qua.append(c)
        return sorted(ket_qua, key=lambda c: c.last_message_at, reverse=True)

    async def list_for_scope(
        self,
        department_ids: list[UUID] | None,
        include_awaiting: bool,
        status: ConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
        q: str | None = None,
    ) -> list[Conversation]:
        return self._loc(department_ids, include_awaiting, status, q)[offset : offset + limit]

    async def count_for_scope(
        self,
        department_ids: list[UUID] | None,
        include_awaiting: bool,
        status: ConversationStatus | None = None,
        q: str | None = None,
    ) -> int:
        return len(self._loc(department_ids, include_awaiting, status, q))


class FakeMessageRepository:
    def __init__(self) -> None:
        self.messages: list[Message] = []
        self._attachments: dict[UUID, list[Attachment]] = {}

    async def add(self, message: Message, attachments: list[Attachment]) -> None:
        self.messages.append(message)
        self._attachments[message.id] = list(attachments)

    async def exists_external(self, external_message_id: str) -> bool:
        return any(m.external_message_id == external_message_id for m in self.messages)

    async def list_for_conversation(
        self, conversation_id: UUID, limit: int = 50, offset: int = 0, newest: bool = False
    ) -> list[Message]:
        ds = [m for m in self.messages if m.conversation_id == conversation_id]
        ds.sort(key=lambda m: m.created_at)
        if newest:
            # Lấy từ cuối lên, rồi trả lại theo thứ tự cũ → mới.
            dau = max(0, len(ds) - offset - limit)
            cuoi = len(ds) - offset
            return ds[dau:cuoi] if cuoi > 0 else []
        return ds[offset : offset + limit]

    async def list_attachments(self, message_id: UUID) -> list[Attachment]:
        return list(self._attachments.get(message_id, []))

    async def last_texts_for_conversations(self, conversation_ids: list[UUID]) -> dict[UUID, str]:
        ket_qua: dict[UUID, str] = {}
        # Tin sắp theo thứ tự thêm vào, nên duyệt xuôi rồi ghi đè sẽ giữ tin
        # cuối cùng — giống ``DISTINCT ON ... ORDER BY created_at DESC`` thật.
        for m in self.messages:
            if m.conversation_id in conversation_ids and m.text:
                ket_qua[m.conversation_id] = m.text
        return ket_qua

    async def get_attachment_with_conversation(
        self, attachment_id: UUID
    ) -> tuple[Attachment, UUID] | None:
        for message_id, ds in self._attachments.items():
            for a in ds:
                if a.id == attachment_id:
                    tin = next((m for m in self.messages if m.id == message_id), None)
                    if tin is None:
                        return None
                    return a, tin.conversation_id
        return None


class FakeCredentialCipher:
    """Mã hoá giả: bọc/tháo tiền tố, đủ để test 'không lưu thô'."""

    _TIEN_TO = "enc::"

    def encrypt(self, plaintext: str) -> str:
        return f"{self._TIEN_TO}{plaintext}"

    def decrypt(self, ciphertext: str) -> str:
        return ciphertext.removeprefix(self._TIEN_TO)


class FakeAttachmentStore:
    def __init__(self) -> None:
        self.saved: list[bytes] = []

    async def save(
        self, data: bytes, suggested_name: str, content_type: str | None
    ) -> StoredAttachment:
        self.saved.append(data)
        return StoredAttachment(
            stored_path=f"var/attachments/{suggested_name}",
            content_type=content_type,
            size=len(data),
        )


class FakeChannelAdapter:
    """Adapter giả cho một nền tảng, do test điều khiển."""

    def __init__(self, platform: Platform, events: list[InboundEvent] | None = None) -> None:
        self._platform = platform
        self._events = events or []
        self.sent: list[tuple[str, MessageContent]] = []
        # Token adapter thực sự nhận — test khẳng định nó đã được giải mã.
        self.sent_tokens: list[str] = []
        self.reject_signature = False

    @property
    def platform(self) -> Platform:
        return self._platform

    def parse_webhook(self, raw_body: bytes, headers: dict[str, str]) -> list[InboundEvent]:
        if self.reject_signature:
            raise ValueError("chữ ký sai")
        return self._events

    async def send_message(
        self,
        access_token: str,
        external_customer_id: str,
        content: MessageContent,
    ) -> SentMessageRef:
        self.sent_tokens.append(access_token)
        self.sent.append((external_customer_id, content))
        return SentMessageRef(external_message_id="sent_1")

    async def download_attachment(self, ref: AttachmentRef) -> bytes:
        return b"noi-dung-anh-gia-lap"


class FakeChannelAdapterRegistry:
    def __init__(self, adapters: list[FakeChannelAdapter]) -> None:
        self._by_platform = {a.platform: a for a in adapters}

    def for_platform(self, platform: Platform) -> FakeChannelAdapter:
        return self._by_platform[platform]


class FakeWorkforceDirectory:
    def __init__(self, agents: list[AgentInfo] | None = None) -> None:
        self._agents: dict[UUID, AgentInfo] = {a.user_id: a for a in (agents or [])}
        self.active_departments: set[UUID] = set()

    async def get_agent(self, user_id: UUID) -> AgentInfo | None:
        return self._agents.get(user_id)

    async def department_exists_active(self, department_id: UUID) -> bool:
        return department_id in self.active_departments


class FakeRealtimeNotifier:
    def __init__(self) -> None:
        self.signals: list[tuple[UUID, UUID | None, str]] = []

    async def notify_conversation_changed(
        self, conversation_id: UUID, department_id: UUID | None, change: str
    ) -> None:
        self.signals.append((conversation_id, department_id, change))
