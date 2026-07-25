"""Use case: nhân viên đánh dấu một hội thoại đã xử lý xong."""

from uuid import UUID

from src.modules.inbox.application.actor import InboxActor
from src.modules.inbox.application.authorization import bao_dam_thao_tac
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.ports import CHANGE_STATUS, IRealtimeNotifier
from src.modules.inbox.domain.repositories.conversation_repository import (
    IConversationRepository,
)
from src.shared.application.exceptions import NotFoundError
from src.shared.application.ports import IClock


class CloseConversation:
    """Đóng một hội thoại đang mở.

    Đóng không phải là kết thúc vĩnh viễn: nếu khách nhắn lại, ``register_incoming``
    của domain sẽ tự mở lại và giữ nguyên người đã nhận.
    """

    def __init__(
        self,
        conversation_repo: IConversationRepository,
        notifier: IRealtimeNotifier,
        clock: IClock,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._notifier = notifier
        self._clock = clock

    async def execute(self, actor: InboxActor, conversation_id: UUID) -> Conversation:
        conversation = await self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError("Không tìm thấy hội thoại.", code="CONVERSATION_NOT_FOUND")
        bao_dam_thao_tac(actor, conversation)

        now = self._clock.now()
        conversation.close(now)
        await self._conversation_repo.update(conversation)

        await self._notifier.notify_conversation_changed(
            conversation.id, conversation.department_id, CHANGE_STATUS
        )
        return conversation
