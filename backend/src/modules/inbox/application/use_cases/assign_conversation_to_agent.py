"""Use case: giao một hội thoại đang mở cho một nhân viên cụ thể.

Khác ``TakeConversation`` (nhân viên tự nhận CHÍNH MÌNH), use case này để
Manager/Admin — hoặc #3 Auto-Assignment với actor hệ thống — giao việc cho MỘT
nhân viên khác. Máy trạng thái ``assign_to_agent`` của domain vẫn là chốt: chỉ
gán khi hội thoại ``DANG_MO`` và chưa có người (không cướp việc).
"""

from uuid import UUID

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.ports import CHANGE_STATUS, IRealtimeNotifier, IWorkforceDirectory
from src.modules.inbox.domain.repositories.conversation_repository import (
    IConversationRepository,
)
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class AssignConversationToAgent:
    """Giao một hội thoại đang mở cho một nhân viên trong phòng của hội thoại."""

    def __init__(
        self,
        conversation_repo: IConversationRepository,
        directory: IWorkforceDirectory,
        notifier: IRealtimeNotifier,
        clock: IClock,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._directory = directory
        self._notifier = notifier
        self._clock = clock

    async def execute(
        self, actor: InboxActor, conversation_id: UUID, user_id: UUID
    ) -> Conversation:
        if actor.role not in (ActorRole.ADMIN, ActorRole.MANAGER):
            raise PermissionDeniedError(
                "Chỉ quản lý hoặc quản trị viên được giao việc.",
                code="ASSIGN_AGENT_REQUIRES_MANAGER",
            )

        conversation = await self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError("Không tìm thấy hội thoại.", code="CONVERSATION_NOT_FOUND")

        # Manager chỉ giao việc trong phòng của mình.
        if actor.role is ActorRole.MANAGER and conversation.department_id != actor.department_id:
            raise PermissionDeniedError(
                "Bạn chỉ được giao việc cho hội thoại thuộc phòng mình.",
                code="ASSIGN_AGENT_OUT_OF_SCOPE",
            )

        # Nhân viên nhận phải tồn tại, đang hoạt động, và thuộc ĐÚNG phòng của
        # hội thoại — không giao việc chéo phòng.
        agent = await self._directory.get_agent(user_id)
        if agent is None or not agent.is_active:
            raise NotFoundError("Không tìm thấy nhân viên đang hoạt động.", code="AGENT_NOT_FOUND")
        if agent.department_id != conversation.department_id:
            raise PermissionDeniedError(
                "Nhân viên không thuộc phòng của hội thoại này.",
                code="AGENT_WRONG_DEPARTMENT",
            )

        now = self._clock.now()
        conversation.assign_to_agent(user_id, now)
        await self._conversation_repo.update(conversation)

        await self._notifier.notify_conversation_changed(
            conversation.id, conversation.department_id, CHANGE_STATUS
        )
        return conversation
