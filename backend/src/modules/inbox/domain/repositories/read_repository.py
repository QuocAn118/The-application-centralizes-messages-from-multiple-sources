"""Port lưu trạng thái đã đọc theo từng người (BE-1)."""

from datetime import datetime
from typing import Protocol
from uuid import UUID


class IReadRepository(Protocol):
    async def mark_read(self, user_id: UUID, conversation_id: UUID, at: datetime) -> None:
        """Đánh dấu người này đã đọc hội thoại tới mốc ``at``; không bao giờ lùi."""
        ...
