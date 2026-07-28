"""Interface repository cho Keyword."""

from typing import Protocol
from uuid import UUID

from src.modules.keyword.domain.entities.keyword import Keyword


class IKeywordRepository(Protocol):
    """Truy xuất từ khoá."""

    async def get_by_id(self, keyword_id: UUID) -> Keyword | None: ...

    async def get_by_normalized(self, department_id: UUID, normalized: str) -> Keyword | None:
        """Từ khoá đã có với đúng dạng chuẩn hoá trong một phòng — để chống trùng."""
        ...

    async def add(self, keyword: Keyword) -> None: ...

    async def update(self, keyword: Keyword) -> None: ...

    async def delete(self, keyword_id: UUID) -> None: ...

    async def list_for_departments(self, department_ids: list[UUID] | None) -> list[Keyword]:
        """Liệt kê từ khoá theo phạm vi phòng.

        ``department_ids=None`` nghĩa là không giới hạn (Admin). Danh sách rỗng
        nghĩa là không phòng nào — trả rỗng.
        """
        ...

    async def list_all_active(self) -> list[Keyword]:
        """Toàn bộ từ khoá của mọi phòng — dùng để khớp khi phân tích hội thoại."""
        ...
