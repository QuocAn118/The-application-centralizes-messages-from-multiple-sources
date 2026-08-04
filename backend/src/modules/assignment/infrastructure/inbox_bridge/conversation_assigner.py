"""Cầu nối assignment → inbox (ghi): giao một hội thoại cho một nhân viên.

Implementation ``IConversationAssigner`` — chỗ DUY NHẤT assignment tác động ngược
vào inbox. Gọi use case ``AssignConversationToAgent`` chính thống của #1 với một
actor hệ thống vai ADMIN, nên máy trạng thái / phân quyền / realtime của inbox
giữ nguyên; đây chỉ là "một Admin tự động giao việc".

Trả ``AssignResult``: ``ASSIGNED`` khi gán được; ``ALREADY_TAKEN`` khi hội thoại
vừa có người khác nhận (race — đã ổn, rời hàng đợi); ``REJECTED`` khi #1 từ chối
vì lý do khác (không còn DANG_MO, nhân viên sai phòng…). Nuốt mọi lỗi — auto-assign
thất bại không được làm hỏng luồng gọi.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.assignment.domain.ports import AssignResult, IAssignmentLog
from src.modules.assignment.domain.value_objects.candidate import AssignmentEvent
from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.assign_conversation_to_agent import (
    AssignConversationToAgent,
)
from src.modules.inbox.domain.entities.conversation import AlreadyAssignedError
from src.modules.inbox.domain.ports import IRealtimeNotifier
from src.modules.inbox.infrastructure.directory.workforce_directory import (
    IdentityWorkforceDirectory,
)
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.shared.application.exceptions import ApplicationError
from src.shared.application.ports import IClock
from src.shared.domain.exceptions import DomainError

logger = logging.getLogger(__name__)

# Actor hệ thống: hành động tự động của #3, không phải người thật. Vai ADMIN để
# giao việc trong bất kỳ phòng nào (Manager chỉ trong phòng mình). user_id danh
# nghĩa, không trỏ tài khoản thật.
_SYSTEM_ACTOR = InboxActor(
    user_id=UUID("00000000-0000-0000-0000-000000000000"),
    role=ActorRole.ADMIN,
    department_id=None,
)


class InboxConversationAssigner:
    """Giao hội thoại cho nhân viên qua use case của inbox, actor hệ thống."""

    def __init__(
        self,
        session: AsyncSession,
        notifier: IRealtimeNotifier,
        clock: IClock,
        log: IAssignmentLog,
    ) -> None:
        self._assign = AssignConversationToAgent(
            conversation_repo=SqlAlchemyConversationRepository(session),
            directory=IdentityWorkforceDirectory(session),
            notifier=notifier,
            clock=clock,
        )
        self._log = log
        self._clock = clock

    async def assign_to_agent(
        self, conversation_id: UUID, user_id: UUID, department_id: UUID | None
    ) -> AssignResult:
        try:
            await self._assign.execute(_SYSTEM_ACTOR, conversation_id, user_id)
        except AlreadyAssignedError:
            # Hội thoại vừa có người khác nhận (race) — đã ổn, rời hàng đợi.
            logger.info(
                "Tự giao việc: hội thoại vừa có người nhận",
                extra={"conversation_id": str(conversation_id)},
            )
            return AssignResult.ALREADY_TAKEN
        except (DomainError, ApplicationError):
            logger.info(
                "Tự giao việc bị khước từ — để hàng đợi",
                extra={"conversation_id": str(conversation_id), "user_id": str(user_id)},
            )
            return AssignResult.REJECTED
        # Gán thành công → ghi một dòng lịch sử (nguồn sự thật cho assigned_count #5).
        # Cùng session/giao dịch với việc gán: hoặc cùng commit, hoặc cùng rollback.
        await self._log.ghi(
            AssignmentEvent(
                conversation_id=conversation_id,
                user_id=user_id,
                department_id=department_id,
                assigned_at=self._clock.now(),
            )
        )
        return AssignResult.ASSIGNED
