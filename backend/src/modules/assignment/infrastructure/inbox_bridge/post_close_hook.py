"""Hook post-close của #3 — kéo hàng đợi phòng khi một nhân viên vừa rảnh.

Trigger: nhân viên đóng một hội thoại (``POST /inbox/{id}/close``) → họ rảnh ra →
kéo các hội thoại đang chờ của phòng đó cho những người trong ca. Nối qua
``app.state.post_close_hooks``: close router (inbox.presentation) chỉ gọi các
callable với ``department_id`` của hội thoại vừa đóng — không import assignment.
Hook thuộc ``assignment.infrastructure`` nên được phép biết cả inbox lẫn use case.

An toàn theo thiết kế:
- Chạy trên **session riêng**, SAU khi #1 đã commit việc đóng.
- Nuốt **mọi** lỗi (log rồi thôi): kéo hàng đợi hỏng không được làm hỏng thao tác
  đóng hội thoại (đã hoàn tất và trả về client).
- Hội thoại vừa đóng chưa được phân phòng (``department_id`` None) → không có việc
  gì để kéo, bỏ qua.
"""

import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.assignment.application.use_cases.pull_department_queue import (
    PullDepartmentQueue,
)
from src.modules.inbox.domain.ports import ClosedConversation

logger = logging.getLogger(__name__)


def make_post_close_hook(
    session_factory_provider: Callable[[], async_sessionmaker[AsyncSession]],
    pull_queue_factory: Callable[[AsyncSession], PullDepartmentQueue],
) -> Callable[[ClosedConversation], Awaitable[None]]:
    """Tạo hook post-close kéo hàng đợi phòng.

    Nhận ``ClosedConversation`` (payload chung của mọi hook post-close); chỉ dùng
    ``department_id`` — ``None`` (chưa phân phòng) thì bỏ qua. ``session_factory_provider``
    đọc **lười** session factory.
    """

    async def hook(closed: ClosedConversation) -> None:
        if closed.department_id is None:
            return
        try:
            session_factory = session_factory_provider()
            async with session_factory() as session:
                await pull_queue_factory(session).execute(closed.department_id)
                await session.commit()
        except Exception:
            logger.exception(
                "Hook kéo hàng đợi sau đóng hội thoại lỗi — bỏ qua",
                extra={"department_id": str(closed.department_id)},
            )

    return hook
