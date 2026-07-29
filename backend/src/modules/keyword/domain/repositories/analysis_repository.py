"""Interface repository cho ConversationAnalysis."""

from typing import Protocol
from uuid import UUID

from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)


class IAnalysisRepository(Protocol):
    """Truy xuất bản ghi phân tích hội thoại."""

    async def get_by_id(self, analysis_id: UUID) -> ConversationAnalysis | None: ...

    async def add(self, analysis: ConversationAnalysis) -> None: ...

    async def list_for_conversation(self, conversation_id: UUID) -> list[ConversationAnalysis]:
        """Lịch sử phân tích của một hội thoại, mới nhất trước."""
        ...

    async def list_for_departments(
        self, department_ids: list[UUID] | None, limit: int = 50, offset: int = 0
    ) -> list[ConversationAnalysis]:
        """Liệt kê phân tích theo phạm vi phòng đề xuất.

        ``department_ids=None`` nghĩa là không giới hạn (Admin). Danh sách rỗng
        nghĩa là không phòng nào. Lọc theo ``suggested_department_id``.
        """
        ...

    async def count_for_departments(self, department_ids: list[UUID] | None) -> int: ...
