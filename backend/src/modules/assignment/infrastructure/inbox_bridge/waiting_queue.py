"""Cầu nối assignment → inbox (đọc): hàng đợi hội thoại chưa gán của một phòng.

Implementation ``IWaitingQueue``. Hàng đợi phòng = hội thoại ``DANG_MO`` thuộc
phòng nhưng chưa có ``assigned_user_id``. Sắp theo **chờ lâu nhất trước**
(``last_message_at`` tăng dần) để kéo công bằng. Đọc thẳng ``ConversationModel``
của inbox (assignment.infrastructure được phép chạm inbox).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.conversation import ConversationStatus
from src.modules.inbox.infrastructure.models.conversation_model import ConversationModel


class InboxWaitingQueue:
    """Đọc hàng đợi phòng từ inbox."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def waiting_conversations(self, department_id: UUID, limit: int = 50) -> tuple[UUID, ...]:
        cau = (
            select(ConversationModel.id)
            .where(
                ConversationModel.department_id == department_id,
                ConversationModel.status == ConversationStatus.DANG_MO.value,
                ConversationModel.assigned_user_id.is_(None),
            )
            .order_by(ConversationModel.last_message_at)
            .limit(limit)
        )
        ket_qua = await self._session.execute(cau)
        return tuple(ket_qua.scalars())
