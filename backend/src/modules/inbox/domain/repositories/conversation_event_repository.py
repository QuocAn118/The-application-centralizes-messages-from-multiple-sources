"""Port lưu timeline sự kiện của hội thoại (BE-2)."""

from typing import Protocol
from uuid import UUID

from src.modules.inbox.domain.entities.conversation_event import ConversationEvent


class IConversationEventRepository(Protocol):
    async def add(self, event: ConversationEvent) -> None: ...

    async def list_for_conversation(self, conversation_id: UUID) -> list[ConversationEvent]:
        """Mọi sự kiện của một hội thoại, cũ trước mới sau."""
        ...
