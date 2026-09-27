"""Use case: Manager/Admin giao, đổi hoặc gỡ người phụ trách (BE-2, redesign 2a).

Khác ``TakeConversation`` (tự nhận) và ``AssignConversationToAgent`` (#3 tự giao,
"không cướp việc"): đây là đường DUY NHẤT được thay người đang phụ trách — quy tắc
mới user duyệt 2026-09-27. Quyền giữ đúng như giao việc sẵn có: Manager chỉ trong
phòng mình, Admin mọi phòng; người được giao đang hoạt động và cùng phòng.

Mỗi lần thành công:
- ghi một sự kiện timeline (nguồn "dòng hệ thống" trong khung chat);
- báo phòng (``status_changed``) + báo RIÊNG người được giao và người bị gỡ.
Router phát thêm hook ``post_assign`` để #3 ghi ``assignment_log`` (không import).
"""

from uuid import UUID

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.entities.conversation_event import (
    ConversationEvent,
    ConversationEventKind,
)
from src.modules.inbox.domain.ports import (
    CHANGE_ASSIGNED_TO_YOU,
    CHANGE_STATUS,
    CHANGE_UNASSIGNED_FROM_YOU,
    IRealtimeNotifier,
    IWorkforceDirectory,
)
from src.modules.inbox.domain.repositories.conversation_event_repository import (
    IConversationEventRepository,
)
from src.modules.inbox.domain.repositories.conversation_repository import (
    IConversationRepository,
)
from src.shared.application.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.shared.application.ports import IClock


class ChangeAssignee:
    def __init__(
        self,
        conversation_repo: IConversationRepository,
        event_repo: IConversationEventRepository,
        directory: IWorkforceDirectory,
        notifier: IRealtimeNotifier,
        clock: IClock,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._event_repo = event_repo
        self._directory = directory
        self._notifier = notifier
        self._clock = clock

    async def execute(
        self, actor: InboxActor, conversation_id: UUID, user_id: UUID | None
    ) -> tuple[Conversation, ConversationEvent]:
        """``user_id=None`` = gỡ người phụ trách. Trả hội thoại + sự kiện vừa ghi."""
        if actor.role not in (ActorRole.ADMIN, ActorRole.MANAGER):
            raise PermissionDeniedError(
                "Chỉ quản lý hoặc quản trị viên được giao việc.",
                code="ASSIGN_AGENT_REQUIRES_MANAGER",
            )
        conversation = await self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError("Không tìm thấy hội thoại.", code="CONVERSATION_NOT_FOUND")
        if actor.role is ActorRole.MANAGER and conversation.department_id != actor.department_id:
            raise PermissionDeniedError(
                "Bạn chỉ được giao việc cho hội thoại thuộc phòng mình.",
                code="ASSIGN_AGENT_OUT_OF_SCOPE",
            )
        if user_id is not None:
            agent = await self._directory.get_agent(user_id)
            if agent is None or not agent.is_active:
                raise NotFoundError(
                    "Không tìm thấy nhân viên đang hoạt động.", code="AGENT_NOT_FOUND"
                )
            if agent.department_id != conversation.department_id:
                raise PermissionDeniedError(
                    "Nhân viên không thuộc phòng của hội thoại này.",
                    code="AGENT_WRONG_DEPARTMENT",
                )

        now = self._clock.now()
        # Entity giữ bất biến (DANG_MO, không đổi sang chính người đó, không gỡ khi
        # trống); repository chốt "không ai đổi chen giữa" bằng so-và-đổi.
        nguoi_cu = conversation.chuyen_nguoi_phu_trach(user_id, now)
        if not await self._conversation_repo.doi_nguoi_phu_trach_neu_chua_doi(
            conversation.id, nguoi_cu, user_id, now
        ):
            raise ConflictError(
                "Người phụ trách vừa được người khác thay đổi. Hãy tải lại hội thoại.",
                code="ASSIGNEE_CHANGED_CONCURRENTLY",
            )

        if nguoi_cu is None:
            kind = ConversationEventKind.ASSIGNED
        elif user_id is None:
            kind = ConversationEventKind.UNASSIGNED
        else:
            kind = ConversationEventKind.REASSIGNED
        su_kien = ConversationEvent.ghi(
            conversation.id,
            kind,
            now,
            actor_user_id=actor.user_id,
            from_user_id=nguoi_cu,
            to_user_id=user_id,
        )
        await self._event_repo.add(su_kien)

        await self._notifier.notify_conversation_changed(
            conversation.id, conversation.department_id, CHANGE_STATUS
        )
        if user_id is not None:
            await self._notifier.notify_user(user_id, conversation.id, CHANGE_ASSIGNED_TO_YOU)
        if nguoi_cu is not None:
            await self._notifier.notify_user(nguoi_cu, conversation.id, CHANGE_UNASSIGNED_FROM_YOU)
        return conversation, su_kien
