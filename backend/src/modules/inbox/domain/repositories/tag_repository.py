"""Port lưu nhãn + nhãn gắn cho khách (BE-6)."""

from typing import Protocol
from uuid import UUID

from src.modules.inbox.domain.entities.tag import Tag


class ITagRepository(Protocol):
    async def add(self, tag: Tag) -> None: ...

    async def update(self, tag: Tag) -> None: ...

    async def get_by_id(self, tag_id: UUID) -> Tag | None: ...

    async def get_many(self, tag_ids: list[UUID]) -> list[Tag]: ...

    async def find_by_name(self, name: str) -> Tag | None:
        """So khớp không phân biệt hoa thường (tên đã gộp khoảng trắng)."""
        ...

    async def list_all(self, include_inactive: bool) -> list[Tag]: ...

    async def list_for_customer(self, customer_id: UUID) -> list[Tag]: ...

    async def set_for_customer(self, customer_id: UUID, tag_ids: list[UUID]) -> None:
        """Thay TOÀN BỘ nhãn của khách bằng ``tag_ids``."""
        ...
