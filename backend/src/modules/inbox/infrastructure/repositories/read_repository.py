"""Implementation ``IReadRepository`` — ghi "đã đọc tới đâu" theo từng người (BE-1)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.infrastructure.models.conversation_read_model import (
    ConversationReadModel,
)


class SqlAlchemyReadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def mark_read(self, user_id: UUID, conversation_id: UUID, at: datetime) -> None:
        """Upsert mốc đã đọc; **không bao giờ lùi**.

        Hai tab cùng mở một hội thoại có thể gửi "đã đọc" lệch thứ tự — mốc cũ tới
        sau mà ghi đè thì tin đã đọc lại hiện là chưa đọc. ``GREATEST`` chặn chuyện đó
        ngay trong một câu lệnh (không đọc-rồi-ghi, nên không đua).
        """
        cau = insert(ConversationReadModel).values(
            user_id=user_id, conversation_id=conversation_id, last_read_at=at
        )
        cau = cau.on_conflict_do_update(
            index_elements=[ConversationReadModel.user_id, ConversationReadModel.conversation_id],
            set_={
                "last_read_at": func.greatest(
                    ConversationReadModel.last_read_at, cau.excluded.last_read_at
                )
            },
        )
        await self._session.execute(cau)
