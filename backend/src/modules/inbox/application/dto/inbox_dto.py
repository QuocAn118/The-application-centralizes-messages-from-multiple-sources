"""DTO đọc cho tầng application của inbox.

Đây là dạng dữ liệu use case trả cho presentation — gộp sẵn thông tin từ nhiều
entity để router không phải tự nối. Chúng thuần dữ liệu, bất biến.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.modules.inbox.domain.entities.conversation import ConversationStatus
from src.modules.inbox.domain.entities.message import MessageDirection
from src.modules.inbox.domain.value_objects.message_content import AttachmentKind
from src.modules.inbox.domain.value_objects.platform import Platform


@dataclass(frozen=True)
class Page[T]:
    """Một trang kết quả cùng tổng số bản ghi khớp bộ lọc."""

    items: list[T]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class InboxItem:
    """Một dòng trong danh sách inbox — đủ để hiển thị mà không mở hội thoại."""

    conversation_id: UUID
    channel_id: UUID
    platform: Platform
    customer_id: UUID
    customer_display_name: str | None
    status: ConversationStatus
    department_id: UUID | None
    assigned_user_id: UUID | None
    last_message_at: datetime
    # Trích ngắn nội dung tin cuối để hiện dưới tên khách. ``None`` khi hội thoại
    # chưa có tin, hoặc tin cuối chỉ có tệp đính kèm (không có phần chữ).
    last_message_preview: str | None = None
    # BE-1: số tin VÀO người gọi chưa đọc (DA_DONG luôn 0).
    unread_count: int = 0
    # BE-9: khách chờ từ lúc nào — tin vào đầu tiên sau tin ra cuối (DA_DONG: None).
    waiting_since: datetime | None = None
    # BE-2: tên người phụ trách, do backend tra (Staff không gọi được /users).
    assigned_user_name: str | None = None


@dataclass(frozen=True)
class AttachmentView:
    """Một tệp đính kèm trong một tin, ở dạng phục vụ lại từ hệ thống."""

    id: UUID
    kind: AttachmentKind
    stored_path: str
    content_type: str | None = None
    size: int | None = None


@dataclass(frozen=True)
class MessageView:
    """Một tin trong hội thoại kèm các tệp đính kèm của nó."""

    id: UUID
    direction: MessageDirection
    text: str | None
    created_at: datetime
    sender_user_id: UUID | None = None
    attachments: tuple[AttachmentView, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EventView:
    """Một dòng hệ thống trong khung chat (BE-2). Tên ``None`` = hệ thống/không rõ."""

    id: UUID
    kind: str
    created_at: datetime
    actor_name: str | None
    from_name: str | None
    to_name: str | None


@dataclass(frozen=True)
class ConversationView:
    """Chi tiết một hội thoại: phần đầu + danh sách tin."""

    conversation_id: UUID
    channel_id: UUID
    platform: Platform
    customer_id: UUID
    customer_display_name: str | None
    status: ConversationStatus
    department_id: UUID | None
    assigned_user_id: UUID | None
    last_message_at: datetime
    messages: tuple[MessageView, ...] = field(default_factory=tuple)
    # BE-9 (xem InboxItem).
    waiting_since: datetime | None = None
    # BE-2 / panel khách (2a).
    assigned_user_name: str | None = None
    customer_external_id: str = ""
    events: tuple[EventView, ...] = field(default_factory=tuple)
