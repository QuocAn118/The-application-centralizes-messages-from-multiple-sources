"""Cầu nối assignment → inbox (ghi): giao một hội thoại cho một nhân viên.

Implementation ``IConversationAssigner`` — chỗ DUY NHẤT assignment tác động ngược
vào inbox. Gọi use case ``AssignConversationToAgent`` chính thống của #1 với một
actor hệ thống vai ADMIN, nên máy trạng thái / phân quyền / realtime của inbox
giữ nguyên; đây chỉ là "một Admin tự động giao việc".

Trả ``True`` nếu gán thành công. Nếu #1 từ chối (hội thoại đã có người, không còn
DANG_MO, nhân viên sai phòng…) thì nuốt lỗi và trả ``False`` — auto-assign thất
bại không được làm hỏng luồng gọi; use case sẽ để hội thoại trong hàng đợi.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.assign_conversation_to_agent import (
    AssignConversationToAgent,
)
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

    def __init__(self, session: AsyncSession, notifier: IRealtimeNotifier, clock: IClock) -> None:
        self._assign = AssignConversationToAgent(
            conversation_repo=SqlAlchemyConversationRepository(session),
            directory=IdentityWorkforceDirectory(session),
            notifier=notifier,
            clock=clock,
        )

    async def assign_to_agent(self, conversation_id: UUID, user_id: UUID) -> bool:
        try:
            await self._assign.execute(_SYSTEM_ACTOR, conversation_id, user_id)
        except (DomainError, ApplicationError):
            logger.info(
                "Tự giao việc bị khước từ — để hàng đợi",
                extra={"conversation_id": str(conversation_id), "user_id": str(user_id)},
            )
            return False
        return True
