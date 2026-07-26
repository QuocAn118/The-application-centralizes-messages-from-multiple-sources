"""Schema cho các endpoint inbox (hội thoại, tin nhắn)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.modules.inbox.application.dto.inbox_dto import (
    ConversationView,
    InboxItem,
    MessageView,
)


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
        )


class AttachmentResponse(BaseModel):
    id: UUID
    kind: str
    stored_path: str
    content_type: str | None
    size: int | None


class MessageResponse(BaseModel):
    id: UUID
    direction: str
    text: str | None
    created_at: datetime
    sender_user_id: UUID | None
    attachments: list[AttachmentResponse]

    @classmethod
    def from_dto(cls, m: MessageView) -> "MessageResponse":
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
    def from_dto(cls, v: ConversationView) -> "ConversationResponse":
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
            messages=[MessageResponse.from_dto(m) for m in v.messages],
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
