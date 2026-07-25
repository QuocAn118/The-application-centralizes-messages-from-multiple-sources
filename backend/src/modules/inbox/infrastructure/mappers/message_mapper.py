"""Chuyển đổi giữa ORM model và domain entity của tin nhắn và tệp đính kèm."""

from src.modules.inbox.domain.entities.attachment import Attachment
from src.modules.inbox.domain.entities.message import Message, MessageDirection
from src.modules.inbox.domain.value_objects.message_content import AttachmentKind
from src.modules.inbox.infrastructure.models.attachment_model import AttachmentModel
from src.modules.inbox.infrastructure.models.message_model import MessageModel


class MessageMapper:
    """Cầu nối giữa bảng ``messages`` và entity ``Message``.

    Tin nhắn không có ``update_model``: tin là bất biến sau khi tạo (không sửa
    nội dung tin đã gửi/nhận).
    """

    @staticmethod
    def to_domain(model: MessageModel) -> Message:
        return Message(
            id=model.id,
            conversation_id=model.conversation_id,
            direction=MessageDirection(model.direction),
            text=model.text,
            external_message_id=model.external_message_id,
            sender_user_id=model.sender_user_id,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: Message) -> MessageModel:
        return MessageModel(
            id=entity.id,
            conversation_id=entity.conversation_id,
            direction=entity.direction.value,
            text=entity.text,
            external_message_id=entity.external_message_id,
            sender_user_id=entity.sender_user_id,
            created_at=entity.created_at,
        )


class AttachmentMapper:
    """Cầu nối giữa bảng ``attachments`` và entity ``Attachment``."""

    @staticmethod
    def to_domain(model: AttachmentModel) -> Attachment:
        return Attachment(
            id=model.id,
            message_id=model.message_id,
            kind=AttachmentKind(model.kind),
            stored_path=model.stored_path,
            original_url=model.original_url,
            content_type=model.content_type,
            size=model.size,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: Attachment) -> AttachmentModel:
        return AttachmentModel(
            id=entity.id,
            message_id=entity.message_id,
            kind=entity.kind.value,
            stored_path=entity.stored_path,
            original_url=entity.original_url,
            content_type=entity.content_type,
            size=entity.size,
            created_at=entity.created_at,
        )
