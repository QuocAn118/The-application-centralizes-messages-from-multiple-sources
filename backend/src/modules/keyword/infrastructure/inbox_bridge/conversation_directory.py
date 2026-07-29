"""Cầu nối keyword → inbox (đọc): chỗ keyword được biết inbox tồn tại.

Implementation của port ``IConversationDirectory``. Đọc trạng thái một hội thoại
và vài tin ĐẦU của khách để dựng ``ConversationSnapshot`` cho use case phân tích.
Nhờ ranh giới này, domain/application/presentation của keyword không import
inbox (import-linter xác nhận).

Chỉ lấy tin **INBOUND** (của khách) có nội dung text — LLM cần hiểu khách nói gì,
không phải câu trả lời của nhân viên; tin chỉ có ảnh (text rỗng) cũng bỏ qua.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.conversation import ConversationStatus
from src.modules.inbox.domain.entities.message import MessageDirection
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.inbox.infrastructure.repositories.message_repository import (
    SqlAlchemyMessageRepository,
)
from src.modules.keyword.domain.ports import ConversationSnapshot

# Quét trong khoảng tin gần đầu để tìm đủ tin khách; đủ rộng để bỏ qua vài tin
# nhân viên hoặc tin chỉ-ảnh xen giữa mà không cần phân trang.
_MESSAGE_SCAN_LIMIT = 20


class InboxConversationDirectory:
    """Đọc hội thoại + vài tin inbound đầu từ inbox, trả kiểu trung lập của keyword."""

    def __init__(self, session: AsyncSession) -> None:
        self._conversation_repo = SqlAlchemyConversationRepository(session)
        self._message_repo = SqlAlchemyMessageRepository(session)

    async def get_snapshot(
        self, conversation_id: UUID, max_messages: int
    ) -> ConversationSnapshot | None:
        conversation = await self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            return None

        # Tin trả về theo thứ tự created_at tăng dần → lấy đúng các tin ĐẦU.
        messages = await self._message_repo.list_for_conversation(
            conversation_id, limit=_MESSAGE_SCAN_LIMIT
        )
        first_texts: list[str] = []
        for message in messages:
            if message.direction is not MessageDirection.INBOUND:
                continue
            if message.text is None or not message.text.strip():
                continue
            first_texts.append(message.text)
            if len(first_texts) >= max_messages:
                break

        return ConversationSnapshot(
            conversation_id=conversation_id,
            is_awaiting=conversation.status is ConversationStatus.CHO_PHAN,
            first_texts=tuple(first_texts),
        )
