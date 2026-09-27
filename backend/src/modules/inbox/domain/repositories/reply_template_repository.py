"""Port lưu mẫu trả lời (BE-7)."""

from typing import Protocol
from uuid import UUID

from src.modules.inbox.domain.entities.reply_template import ReplyTemplate


class IReplyTemplateRepository(Protocol):
    async def add(self, template: ReplyTemplate) -> None: ...

    async def update(self, template: ReplyTemplate) -> None: ...

    async def get_by_id(self, template_id: UUID) -> ReplyTemplate | None: ...

    async def delete(self, template_id: UUID) -> None: ...

    async def list_visible(
        self, *, tat_ca: bool, department_id: UUID | None
    ) -> list[ReplyTemplate]:
        """``tat_ca`` (Admin): mọi mẫu. Ngược lại: mẫu dùng chung + mẫu của ``department_id``."""
        ...
