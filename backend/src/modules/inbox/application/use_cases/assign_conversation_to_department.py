"""Use case: Manager/Admin phân một hội thoại chờ-phân về một phòng.

Ở #1 việc phân là thủ công. Ở #3, Auto-assignment sẽ thay chỗ này bằng suy luận
từ nội dung — nhưng vẫn gọi cùng phương thức miền ``assign_to_department``, nên
máy trạng thái không đổi.
"""

from uuid import UUID

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.entities.conversation_event import (
    ConversationEvent,
    ConversationEventKind,
)
from src.modules.inbox.domain.ports import CHANGE_STATUS, IRealtimeNotifier, IWorkforceDirectory
from src.modules.inbox.domain.repositories.conversation_event_repository import (
    IConversationEventRepository,
)
from src.modules.inbox.domain.repositories.conversation_repository import (
    IConversationRepository,
)
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class AssignConversationToDepartment:
    """Phân một hội thoại đang chờ về một phòng ban đang hoạt động."""

    def __init__(
        self,
        conversation_repo: IConversationRepository,
        directory: IWorkforceDirectory,
        notifier: IRealtimeNotifier,
        clock: IClock,
        event_repo: IConversationEventRepository | None = None,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._directory = directory
        self._notifier = notifier
        self._clock = clock
        # 2b: dòng hệ thống "A phân về Phòng X" / "Tự động chuyển tới Phòng X".
        self._event_repo = event_repo

    async def execute(
        self,
        actor: InboxActor,
        conversation_id: UUID,
        department_id: UUID,
        *,
        tu_dong: bool = False,
        ly_do: str | None = None,
    ) -> Conversation:
        """``tu_dong`` = #2 tự phân (actor hệ thống); ``ly_do`` hiện sau dấu gạch."""
        if actor.role not in (ActorRole.ADMIN, ActorRole.MANAGER):
            raise PermissionDeniedError(
                "Chỉ quản lý hoặc quản trị viên được phân hội thoại.",
                code="ASSIGN_REQUIRES_MANAGER",
            )

        conversation = await self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError("Không tìm thấy hội thoại.", code="CONVERSATION_NOT_FOUND")

        # Manager chỉ được phân về đúng phòng của mình.
        if actor.role is ActorRole.MANAGER and department_id != actor.department_id:
            raise PermissionDeniedError(
                "Bạn chỉ được phân hội thoại về phòng của mình.",
                code="ASSIGN_OUT_OF_SCOPE",
            )

        if not await self._directory.department_exists_active(department_id):
            raise NotFoundError(
                "Không tìm thấy phòng ban đang hoạt động.", code="DEPARTMENT_NOT_FOUND"
            )

        now = self._clock.now()
        conversation.assign_to_department(department_id, now)
        await self._conversation_repo.update(conversation)
        if self._event_repo is not None:
            await self._event_repo.add(
                ConversationEvent.ghi(
                    conversation.id,
                    ConversationEventKind.AUTO_ROUTED
                    if tu_dong
                    else ConversationEventKind.DEPARTMENT_ASSIGNED,
                    now,
                    actor_user_id=None if tu_dong else actor.user_id,
                    department_id=department_id,
                    detail=ly_do,
                )
            )

        await self._notifier.notify_conversation_changed(
            conversation.id, conversation.department_id, CHANGE_STATUS
        )
        return conversation
