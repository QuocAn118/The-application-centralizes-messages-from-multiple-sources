"""Use case "đã đọc" theo từng người (BE-1, redesign Phần 2a).

- ``MarkConversationRead``: ghi mốc đã đọc của người gọi cho một hội thoại. FE gọi
  khi mở hội thoại và khi có tin mới lúc hội thoại đang mở + tab đang focus. Việc
  "trả lời thì coi như đã đọc" nằm trong ``ReplyToConversation`` (không trông FE).
- ``CountUnreadConversations``: số hội thoại trong phạm vi có tin chưa đọc — cho
  huy hiệu trên thanh điều hướng.
"""

from uuid import UUID

from src.modules.inbox.application.actor import InboxActor
from src.modules.inbox.application.authorization import bao_dam_thao_tac
from src.modules.inbox.application.use_cases.list_inbox import pham_vi_cua
from src.modules.inbox.domain.repositories.conversation_repository import (
    IConversationRepository,
)
from src.modules.inbox.domain.repositories.read_repository import IReadRepository
from src.shared.application.exceptions import NotFoundError
from src.shared.application.ports import IClock


class MarkConversationRead:
    """Người gọi đánh dấu đã đọc một hội thoại. Quyền = quyền xem hội thoại đó."""

    def __init__(
        self,
        conversation_repo: IConversationRepository,
        read_repo: IReadRepository,
        clock: IClock,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._read_repo = read_repo
        self._clock = clock

    async def execute(self, actor: InboxActor, conversation_id: UUID) -> None:
        conversation = await self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError("Không tìm thấy hội thoại.", code="CONVERSATION_NOT_FOUND")
        # Cùng cửa với GET /inbox/{id}: không xem được thì cũng không "đọc" được —
        # không để lộ sự tồn tại của hội thoại phòng khác qua endpoint này.
        bao_dam_thao_tac(actor, conversation)
        await self._read_repo.mark_read(actor.user_id, conversation.id, self._clock.now())


class CountUnreadConversations:
    """Số hội thoại trong phạm vi người gọi có tin vào chưa đọc (bỏ DA_DONG)."""

    def __init__(self, conversation_repo: IConversationRepository) -> None:
        self._conversation_repo = conversation_repo

    async def execute(self, actor: InboxActor) -> int:
        pv = pham_vi_cua(actor)
        return await self._conversation_repo.count_unread_for_scope(
            pv.department_ids, pv.include_awaiting, actor.user_id
        )
