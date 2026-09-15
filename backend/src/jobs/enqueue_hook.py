"""Hook post-ingest phiên bản hàng đợi: chỉ ĐẨY job rồi trả về ngay.

Thay cho hook cũ (gọi LLM đồng bộ trong webhook). Việc duy nhất chạy trong
request là: tra ``conversation_id`` từ sự kiện, rồi ``defer`` một job. Không gọi
LLM, không chờ.

Áp dụng cho **mọi nền tảng** (Telegram, Zalo, Meta) vì webhook router dùng chung
một danh sách ``post_ingest_hooks`` — không có nhánh riêng theo nền tảng.
"""

import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.inbox.domain.ports import InboundEvent

logger = logging.getLogger(__name__)


def make_enqueue_hook(
    session_factory_provider: Callable[[], async_sessionmaker[AsyncSession]],
) -> Callable[[InboundEvent], Awaitable[None]]:
    """Tạo hook đẩy job phân tích vào hàng đợi.

    ``session_factory_provider()`` đọc **lười** vì session factory chỉ có sau khi
    app khởi động (lifespan) — giống hook cũ.

    Nuốt mọi lỗi: hàng đợi hỏng không được làm hỏng việc nhận tin. Mất một job
    phân tích chỉ nghĩa là hội thoại ở lại ``CHO_PHAN`` cho Manager phân tay —
    đúng hành vi dự phòng đã có.
    """

    async def hook(event: InboundEvent) -> None:
        from src.jobs.app import app
        from src.jobs.tasks import phan_tich_hoi_thoai
        from src.modules.keyword.infrastructure.inbox_bridge.conversation_directory import (
            InboxConversationDirectory,
        )

        try:
            session_factory = session_factory_provider()
            async with session_factory() as session:
                conversation_id = await InboxConversationDirectory(session).resolve_conversation_id(
                    event.platform, event.external_channel_id, event.external_customer_id
                )
            if conversation_id is None:
                return

            # ``defer_async`` chỉ INSERT một dòng vào ``procrastinate_jobs`` rồi
            # trả về — mili-giây, không phải vài giây như gọi LLM.
            async with app.open_async():
                await phan_tich_hoi_thoai.defer_async(conversation_id=str(conversation_id))
        except Exception:
            logger.exception(
                "Không đẩy được job phân tích — bỏ qua, tin vẫn nguyên",
                extra={"external_message_id": event.external_message_id},
            )

    return hook
