"""Hook chạy sau khi một tin đến được ingest — kích hoạt phân tích #2.

Đây là chỗ #2 móc vào luồng nhận tin của #1 mà KHÔNG phá ranh giới inbox⊥keyword:
webhook router (thuộc ``inbox.presentation``) chỉ gọi các callable trong
``app.state.post_ingest_hooks`` với ``InboundEvent`` — nó không import keyword.
Composition root (main.py) đăng ký hook này; hook thuộc ``keyword.infrastructure``
nên được phép biết cả inbox lẫn use case keyword.

An toàn theo thiết kế:
- Chạy trên **session riêng**, SAU khi #1 đã commit tin → đọc được tin vừa lưu và
  không đụng giao dịch ingest.
- Nuốt **mọi** lỗi (log rồi thôi): phân tích/LLM hỏng không được làm hỏng nhận
  tin. ``AnalyzeConversation`` vốn đã nuốt lỗi LLM; hook bọc thêm một lớp cho lỗi
  hạ tầng (tra hội thoại, commit…).
"""

import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.inbox.domain.ports import InboundEvent
from src.modules.keyword.application.use_cases.analyze_conversation import (
    AnalyzeConversation,
)
from src.modules.keyword.infrastructure.inbox_bridge.conversation_directory import (
    InboxConversationDirectory,
)

logger = logging.getLogger(__name__)


def make_post_ingest_hook(
    session_factory_provider: Callable[[], async_sessionmaker[AsyncSession]],
    analyze_factory: Callable[[AsyncSession], AnalyzeConversation],
) -> Callable[[InboundEvent], Awaitable[None]]:
    """Tạo hook post-ingest gắn với cách lấy session factory + dựng use case.

    ``session_factory_provider()`` trả session factory hiện tại — đọc **lười** vì
    factory chỉ có sau khi app khởi động (lifespan) hoặc bị test ghi đè, đều SAU
    khi wiring chạy. ``analyze_factory(session)`` dựng ``AnalyzeConversation`` cho
    một session cụ thể. Trả callable ``async (event) -> None`` cho ``post_ingest_hooks``.
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
                await analyze_factory(session).execute(conversation_id)
                await session.commit()
        except Exception:
            logger.exception(
                "Hook phân tích sau ingest lỗi — bỏ qua, tin vẫn nguyên",
                extra={"external_message_id": event.external_message_id},
            )

    return hook
