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
