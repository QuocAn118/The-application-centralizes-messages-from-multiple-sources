"""Cầu nối keyword → inbox (đọc): chỗ keyword được biết inbox tồn tại.

Implementation của port ``IConversationDirectory``. Đọc trạng thái một hội thoại
và vài tin ĐẦU của khách để dựng ``ConversationSnapshot`` cho use case phân tích.
Nhờ ranh giới này, domain/application/presentation của keyword không import
inbox (import-linter xác nhận).

Chỉ lấy tin **INBOUND** (của khách) có nội dung text — LLM cần hiểu khách nói gì,
không phải câu trả lời của nhân viên; tin chỉ có ảnh (text rỗng) cũng bỏ qua.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.conversation import ConversationStatus
from src.modules.inbox.domain.entities.message import MessageDirection
from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.repositories.channel_repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.inbox.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from src.modules.inbox.infrastructure.repositories.message_repository import (
    SqlAlchemyMessageRepository,
)
from src.modules.keyword.domain.ports import ConversationSnapshot

# Quét trong khoảng tin gần đầu để tìm đủ tin khách; đủ rộng để bỏ qua vài tin
# nhân viên hoặc tin chỉ-ảnh xen giữa mà không cần phân trang.
#
# NỢ (chấp nhận): nếu khách gửi hơn _MESSAGE_SCAN_LIMIT tin CHỈ-ẢNH liên tiếp
# trước tin text đầu tiên, snapshot sẽ rỗng và hội thoại giữ CHO_PHAN (an toàn —
# Manager phân tay). Với hội thoại CHO_PHAN, các tin đầu vốn là tin khách (chưa
# có nhân viên nên không có OUTBOUND), nên kịch bản này cực hiếm. Nếu cần chắc
# chắn: thêm truy vấn "N tin INBOUND có text đầu tiên" vào IMessageRepository #1.
_MESSAGE_SCAN_LIMIT = 20


class InboxConversationDirectory:
    """Đọc hội thoại + vài tin inbound đầu từ inbox, trả kiểu trung lập của keyword."""

    def __init__(self, session: AsyncSession) -> None:
        self._channel_repo = SqlAlchemyChannelRepository(session)
        self._customer_repo = SqlAlchemyCustomerRepository(session)
        self._conversation_repo = SqlAlchemyConversationRepository(session)
        self._message_repo = SqlAlchemyMessageRepository(session)

    async def resolve_conversation_id(
        self, platform: Platform, external_channel_id: str, external_customer_id: str
    ) -> UUID | None:
        """Tra ``conversation_id`` từ định danh ngoài của một sự kiện webhook.

        Lặp lại đúng cách ``IngestInboundMessage`` tìm hội thoại (kênh theo external
        → khách theo external → hội thoại đang mở của cặp đó), để hook post-ingest
        biết vừa có tin vào hội thoại nào mà KHÔNG cần #1 đổi hợp đồng trả về.
        Trả ``None`` nếu chưa dựng đủ (kênh/khách/hội thoại chưa có).
        """
        channel = await self._channel_repo.get_by_external(platform, external_channel_id)
        if channel is None:
            return None
        customer = await self._customer_repo.get_by_external(channel.id, external_customer_id)
        if customer is None:
            return None
        conversation = await self._conversation_repo.get_open_for(channel.id, customer.id)
        return conversation.id if conversation is not None else None

    async def get_snapshot(
        self, conversation_id: UUID, max_messages: int
    ) -> ConversationSnapshot | None:
        conversation = await self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            return None

        # Tin trả về theo thứ tự created_at tăng dần → lấy đúng các tin ĐẦU.
        messages = await self._message_repo.list_for_conversation(
            conversation_id, limit=_MESSAGE_SCAN_LIMIT
        )
        first_texts: list[str] = []
        for message in messages:
            if message.direction is not MessageDirection.INBOUND:
                continue
            if message.text is None or not message.text.strip():
                continue
            first_texts.append(message.text)
            if len(first_texts) >= max_messages:
                break

        return ConversationSnapshot(
            conversation_id=conversation_id,
            is_awaiting=conversation.status is ConversationStatus.CHO_PHAN,
            first_texts=tuple(first_texts),
        )
