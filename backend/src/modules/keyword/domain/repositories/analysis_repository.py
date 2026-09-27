"""Interface repository cho ConversationAnalysis."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)
from src.modules.keyword.domain.value_objects.extracted_term import AnalysisOutcome


class IAnalysisRepository(Protocol):
    """Truy xuất bản ghi phân tích hội thoại."""

    async def get_by_id(self, analysis_id: UUID) -> ConversationAnalysis | None: ...

    async def add(self, analysis: ConversationAnalysis) -> None: ...

    async def list_for_conversation(self, conversation_id: UUID) -> list[ConversationAnalysis]:
        """Lịch sử phân tích của một hội thoại, mới nhất trước."""
        ...

    async def list_for_departments(
        self,
        department_ids: list[UUID] | None,
        limit: int = 50,
        offset: int = 0,
        *,
        kem_cho_phan: bool = False,
        outcomes: Sequence[AnalysisOutcome] | None = None,
    ) -> list[ConversationAnalysis]:
        """Liệt kê phân tích theo phạm vi, mới nhất trước.

        ``department_ids=None`` nghĩa là không giới hạn (Admin). Danh sách rỗng
        nghĩa là không phòng nào. Lọc theo ``suggested_department_id``;
        ``kem_cho_phan`` cộng thêm mọi phân tích của hội thoại HIỆN đang chờ phân
        (chưa thuộc phòng nào). ``outcomes`` khác ``None`` thì chỉ giữ các kết cục đó.
        """
        ...

    async def count_for_departments(
        self,
        department_ids: list[UUID] | None,
        *,
        kem_cho_phan: bool = False,
        outcomes: Sequence[AnalysisOutcome] | None = None,
    ) -> int: ...
