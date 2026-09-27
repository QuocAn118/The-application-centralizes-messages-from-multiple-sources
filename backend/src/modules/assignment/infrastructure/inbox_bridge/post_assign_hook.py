"""Hook post-assign của #3 — ghi ``assignment_log`` khi Manager/Admin giao việc tay.

Trigger: ``POST /inbox/{id}/assign-user`` (BE-2) đã commit. Chỉ GIAO / ĐỔI mới là
"một lần được gán" cho người MỚI (nguồn ``assigned_count`` của #5); GỠ không có
người nhận nên bỏ qua. Nối qua ``app.state.post_assign_hooks`` — inbox không import
assignment. Session riêng, nuốt mọi lỗi như hook post-close.
"""

import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.assignment.domain.value_objects.candidate import AssignmentEvent
from src.modules.assignment.infrastructure.persistence.assignment_log_repository import (
    SqlAlchemyAssignmentLog,
)
from src.modules.inbox.domain.ports import AssigneeChanged

logger = logging.getLogger(__name__)


def make_post_assign_hook(
    session_factory_provider: Callable[[], async_sessionmaker[AsyncSession]],
) -> Callable[[AssigneeChanged], Awaitable[None]]:
    async def hook(doi: AssigneeChanged) -> None:
        if doi.to_user_id is None:
            return
        try:
            async with session_factory_provider()() as session:
                await SqlAlchemyAssignmentLog(session).ghi(
                    AssignmentEvent(
                        conversation_id=doi.conversation_id,
                        user_id=doi.to_user_id,
                        department_id=doi.department_id,
                        assigned_at=doi.at,
                    )
                )
                await session.commit()
        except Exception:
            logger.exception(
                "Hook ghi assignment_log sau giao việc tay lỗi — bỏ qua",
                extra={"conversation_id": str(doi.conversation_id)},
            )

    return hook
