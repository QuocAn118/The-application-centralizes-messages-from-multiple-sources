"""Hook post-ingest của #3 — tự gán nhân viên sau khi #2 phân phòng.

Chuỗi trigger tự động: webhook nhận tin (#1) → hook #2 phân hội thoại về phòng →
**hook #3 này** chọn một nhân viên trong phòng và gán. Cả ba nối qua
``app.state.post_ingest_hooks`` theo thứ tự đăng ký (composition root đăng ký #2
trước #3) nên khi hook này chạy, #2 đã commit việc phân phòng ở session riêng của
nó và hội thoại đã ``DANG_MO`` có ``department_id``.

Giữ ranh giới inbox⊥assignment: webhook router (inbox.presentation) chỉ gọi các
callable trong ``post_ingest_hooks`` với ``InboundEvent`` — không import assignment.
Hook thuộc ``assignment.infrastructure`` nên được phép biết cả inbox lẫn use case
assignment.

An toàn theo thiết kế:
- Chạy trên **session riêng**, SAU khi #1/#2 đã commit.
- Chỉ gán khi hội thoại đang ``DANG_MO``, có phòng và **chưa có người** (RB: không
  cướp việc; hội thoại còn ``CHO_PHAN`` nghĩa là #2 chưa phân được phòng → bỏ qua).
- Nuốt **mọi** lỗi (log rồi thôi): auto-assign hỏng không được làm hỏng nhận tin.
"""

import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.assignment.application.use_cases.auto_assign_conversation import (
    AutoAssignConversation,
)
from src.modules.inbox.domain.entities.conversation import ConversationStatus
from src.modules.inbox.domain.ports import InboundEvent
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.keyword.infrastructure.inbox_bridge.conversation_directory import (
    InboxConversationDirectory,
)

logger = logging.getLogger(__name__)


def make_post_ingest_hook(
    session_factory_provider: Callable[[], async_sessionmaker[AsyncSession]],
    auto_assign_factory: Callable[[AsyncSession], AutoAssignConversation],
) -> Callable[[InboundEvent], Awaitable[None]]:
    """Tạo hook post-ingest tự gán nhân viên.

    ``session_factory_provider()`` trả session factory hiện tại — đọc **lười** vì
    factory chỉ có sau khi app khởi động/bị test ghi đè (đều SAU wiring).
    ``auto_assign_factory(session)`` dựng ``AutoAssignConversation`` cho một session.
    """

    async def hook(event: InboundEvent) -> None:
        try:
            session_factory = session_factory_provider()
            async with session_factory() as session:
                conversation_id = await InboxConversationDirectory(session).resolve_conversation_id(
                    event.platform, event.external_channel_id, event.external_customer_id
                )
                if conversation_id is None:
                    return

                conversation = await SqlAlchemyConversationRepository(session).get_by_id(
                    conversation_id
                )
                # Chỉ tự gán khi #2 đã phân được phòng (DANG_MO + có phòng) và chưa
                # ai nhận. CHO_PHAN (chưa phân phòng) hoặc đã có người → bỏ qua.
                if (
                    conversation is None
                    or conversation.status is not ConversationStatus.DANG_MO
                    or conversation.department_id is None
                    or conversation.assigned_user_id is not None
                ):
                    return

                await auto_assign_factory(session).execute(
                    conversation_id, conversation.department_id
                )
                await session.commit()
        except Exception:
            logger.exception(
                "Hook tự gán sau ingest lỗi — bỏ qua, tin vẫn nguyên",
                extra={"external_message_id": event.external_message_id},
            )

    return hook
