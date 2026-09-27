"""Implementation ``IConversationEventRepository`` trên PostgreSQL (BE-2)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.conversation_event import (
    ConversationEvent,
    ConversationEventKind,
)
from src.modules.inbox.infrastructure.models.conversation_event_model import (
    ConversationEventModel,
)


class SqlAlchemyConversationEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: ConversationEvent) -> None:
        self._session.add(
            ConversationEventModel(
                id=event.id,
                conversation_id=event.conversation_id,
                kind=event.kind.value,
                actor_user_id=event.actor_user_id,
                from_user_id=event.from_user_id,
                to_user_id=event.to_user_id,
                created_at=event.created_at,
            )
        )

    async def list_for_conversation(self, conversation_id: UUID) -> list[ConversationEvent]:
        cau = (
            select(ConversationEventModel)
            .where(ConversationEventModel.conversation_id == conversation_id)
            # ``id`` (UUIDv7) phá hoà khi hai sự kiện cùng mốc thời gian.
            .order_by(ConversationEventModel.created_at, ConversationEventModel.id)
        )
        ket_qua = await self._session.execute(cau)
        return [
            ConversationEvent(
                id=m.id,
                conversation_id=m.conversation_id,
                kind=ConversationEventKind(m.kind),
                actor_user_id=m.actor_user_id,
                from_user_id=m.from_user_id,
                to_user_id=m.to_user_id,
                created_at=m.created_at,
            )
            for m in ket_qua.scalars()
        ]
