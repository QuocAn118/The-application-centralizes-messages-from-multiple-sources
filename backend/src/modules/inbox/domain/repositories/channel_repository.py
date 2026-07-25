"""Interface repository cho Channel."""

from typing import Protocol
from uuid import UUID

from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.value_objects.platform import Platform


class IChannelRepository(Protocol):
    """Truy xuất kênh."""

    async def get_by_id(self, channel_id: UUID) -> Channel | None: ...

    async def get_by_external(self, platform: Platform, external_channel_id: str) -> Channel | None:
        """Tra kênh theo (nền tảng + mã kênh) — webhook dùng để tìm kênh đích."""
        ...

    async def add(self, channel: Channel) -> None: ...

    async def update(self, channel: Channel) -> None: ...

    async def list_all(self, is_active: bool | None = None) -> list[Channel]: ...
