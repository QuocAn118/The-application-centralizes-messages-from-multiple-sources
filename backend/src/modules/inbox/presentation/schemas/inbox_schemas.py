"""Schema cho các endpoint inbox (hội thoại, tin nhắn)."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.modules.inbox.application.dto.inbox_dto import (
    ConversationView,
    InboxItem,
    MessageView,
)

# Hàm dựng URL đã ký cho một tệp đính kèm: (attachment_id, conversation_id) → URL.
# Nhận vào dạng callable để tầng schema không phải biết bộ ký hay router.
KyUrl = Callable[[UUID, UUID], str]


class InboxItemResponse(BaseModel):
    conversation_id: UUID
    channel_id: UUID
    platform: str
    customer_id: UUID
    customer_display_name: str | None
    status: str
    department_id: UUID | None
    assigned_user_id: UUID | None
    last_message_at: datetime
    last_message_preview: str | None = None

    @classmethod
    def from_dto(cls, item: InboxItem) -> "InboxItemResponse":
        return cls(
            conversation_id=item.conversation_id,
            channel_id=item.channel_id,
            platform=item.platform.value,
            customer_id=item.customer_id,
            customer_display_name=item.customer_display_name,
            status=item.status.value,
            department_id=item.department_id,
            assigned_user_id=item.assigned_user_id,
            last_message_at=item.last_message_at,
            last_message_preview=item.last_message_preview,
        )


class AttachmentResponse(BaseModel):
    """Tệp đính kèm trả về cho client.

    ``url`` là liên kết đã ký, hết hạn sau ít phút — dùng thẳng được trong thẻ
    ``<img>``. ``stored_path`` là đường dẫn nội bộ, giữ lại để truy vết chứ
    client không dựng URL từ nó.
    """

    id: UUID
    kind: str
    stored_path: str
    content_type: str | None
    size: int | None
    url: str | None = None


class MessageResponse(BaseModel):
    id: UUID
    direction: str
    text: str | None
    created_at: datetime
    sender_user_id: UUID | None
    attachments: list[AttachmentResponse]

    @classmethod
    def from_dto(
        cls,
        m: MessageView,
        ky_url: KyUrl | None = None,
        conversation_id: UUID | None = None,
    ) -> "MessageResponse":
        """Dựng response; nếu có ``ky_url`` thì đính kèm được cấp URL đã ký.

        Hai tham số cuối tuỳ chọn để nơi gọi cũ (chưa cần URL) không phải đổi.
        """
        return cls(
            id=m.id,
            direction=m.direction.value,
            text=m.text,
            created_at=m.created_at,
            sender_user_id=m.sender_user_id,
            attachments=[
                AttachmentResponse(
                    id=a.id,
                    kind=a.kind.value,
                    stored_path=a.stored_path,
                    content_type=a.content_type,
                    size=a.size,
                    url=(
                        ky_url(a.id, conversation_id)
                        if ky_url is not None and conversation_id is not None
                        else None
                    ),
                )
                for a in m.attachments
            ],
        )


class ConversationResponse(BaseModel):
    conversation_id: UUID
    channel_id: UUID
    platform: str
    customer_id: UUID
    customer_display_name: str | None
    status: str
    department_id: UUID | None
    assigned_user_id: UUID | None
    last_message_at: datetime
    messages: list[MessageResponse]

    @classmethod
    def from_dto(cls, v: ConversationView, ky_url: KyUrl | None = None) -> "ConversationResponse":
        return cls(
            conversation_id=v.conversation_id,
            channel_id=v.channel_id,
            platform=v.platform.value,
            customer_id=v.customer_id,
            customer_display_name=v.customer_display_name,
            status=v.status.value,
            department_id=v.department_id,
            assigned_user_id=v.assigned_user_id,
            last_message_at=v.last_message_at,
            messages=[MessageResponse.from_dto(m, ky_url, v.conversation_id) for m in v.messages],
        )


class ReplyRequest(BaseModel):
    """Trả lời hội thoại. Ở #1 gửi text; đính kèm để iteration sau."""

    text: str | None = Field(default=None, max_length=8000)

    @model_validator(mode="after")
    def _co_noi_dung(self) -> "ReplyRequest":
        if self.text is None or not self.text.strip():
            raise ValueError("Tin trả lời phải có nội dung.")
        return self


class AssignRequest(BaseModel):
    department_id: UUID
