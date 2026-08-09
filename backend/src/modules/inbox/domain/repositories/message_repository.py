"""Interface repository cho Message và Attachment."""

from typing import Protocol
from uuid import UUID

from src.modules.inbox.domain.entities.attachment import Attachment
from src.modules.inbox.domain.entities.message import Message


class IMessageRepository(Protocol):
    """Truy xuất tin nhắn và tệp đính kèm."""

    async def add(self, message: Message, attachments: list[Attachment]) -> None:
        """Lưu một tin cùng các tệp đính kèm của nó trong một thao tác."""
        ...

    async def exists_external(self, external_message_id: str) -> bool:
        """Đã xử lý mã tin này của nền tảng chưa — chốt idempotency cho webhook."""
        ...

    async def list_for_conversation(
        self, conversation_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Message]: ...

    async def list_attachments(self, message_id: UUID) -> list[Attachment]: ...

    async def get_attachment_with_conversation(
        self, attachment_id: UUID
    ) -> tuple[Attachment, UUID] | None:
        """Trả ``(tệp, conversation_id)`` để nơi gọi kiểm quyền trên hội thoại."""
        ...

    async def last_texts_for_conversations(self, conversation_ids: list[UUID]) -> dict[UUID, str]:
        """Nội dung chữ của tin cuối mỗi hội thoại — một truy vấn cho cả trang."""
        ...
