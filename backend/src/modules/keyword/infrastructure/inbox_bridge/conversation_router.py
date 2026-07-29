"""Cầu nối keyword → inbox (ghi): tự phân một hội thoại về phòng.

Implementation của port ``IConversationRouter`` — chỗ DUY NHẤT keyword tác động
ngược vào inbox. Gọi đúng use case phân chính thống của #1
(``AssignConversationToDepartment``) với một actor hệ thống vai ADMIN, nên máy
trạng thái / phân quyền / realtime của inbox giữ nguyên; đây chỉ là "một Admin
tự động" thay cho Manager phân tay.

Trả ``True`` nếu phân thành công. Nếu #1 từ chối (hội thoại không còn CHO_PHAN,
phòng không hoạt động, v.v.) thì nuốt lỗi và trả ``False`` — phân tự động thất
bại không được làm hỏng luồng nhận tin; use case keyword sẽ ghi nhận mơ hồ.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.assign_conversation_to_department import (
    AssignConversationToDepartment,
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

# Actor hệ thống: hành động tự động của #2, không phải người thật. Vai ADMIN để
# được phân về BẤT KỲ phòng nào (Manager chỉ phân về phòng mình). user_id là
# UUID danh nghĩa, không trỏ tới tài khoản có thật.
_SYSTEM_ACTOR = InboxActor(
    user_id=UUID("00000000-0000-0000-0000-000000000000"),
    role=ActorRole.ADMIN,
    department_id=None,
)


class InboxConversationRouter:
    """Tự phân hội thoại về phòng qua use case phân của inbox."""

    def __init__(self, session: AsyncSession, notifier: IRealtimeNotifier, clock: IClock) -> None:
        self._assign = AssignConversationToDepartment(
            conversation_repo=SqlAlchemyConversationRepository(session),
            directory=IdentityWorkforceDirectory(session),
            notifier=notifier,
            clock=clock,
        )

    async def assign_to_department(self, conversation_id: UUID, department_id: UUID) -> bool:
        try:
            await self._assign.execute(_SYSTEM_ACTOR, conversation_id, department_id)
        except (DomainError, ApplicationError):
            logger.warning(
                "Tự phân hội thoại thất bại — giữ CHO_PHAN",
                extra={
                    "conversation_id": str(conversation_id),
                    "department_id": str(department_id),
                },
            )
            return False
        return True
