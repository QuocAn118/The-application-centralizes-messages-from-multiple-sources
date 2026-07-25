"""Interface repository cho Conversation."""

from typing import Protocol
from uuid import UUID

from src.modules.inbox.domain.entities.conversation import (
    Conversation,
    ConversationStatus,
)


class IConversationRepository(Protocol):
    """Truy xuất hội thoại."""

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None: ...

    async def get_open_for(self, channel_id: UUID, customer_id: UUID) -> Conversation | None:
        """Hội thoại chưa đóng của một cặp (kênh, khách), nếu có.

        Webhook dùng để nối tin mới vào hội thoại đang mở/chờ, thay vì tạo mới.
        """
        ...

    async def add(self, conversation: Conversation) -> None: ...

    async def update(self, conversation: Conversation) -> None: ...

    async def list_for_scope(
        self,
        department_ids: list[UUID] | None,
        include_awaiting: bool,
        status: ConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """Liệt kê hội thoại trong phạm vi phòng ban cho phép.

        ``department_ids=None`` nghĩa là không giới hạn phòng (Admin). Danh sách
        rỗng nghĩa là không phòng nào — không trả gì. ``include_awaiting`` gộp
        thêm mục chờ-phân (cho Manager/Admin).
        """
        ...

    async def count_for_scope(
        self,
        department_ids: list[UUID] | None,
        include_awaiting: bool,
        status: ConversationStatus | None = None,
    ) -> int: ...
