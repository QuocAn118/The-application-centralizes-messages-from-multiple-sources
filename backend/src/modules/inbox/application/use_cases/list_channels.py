"""Use case: Admin liệt kê các kênh đã kết nối."""

from src.modules.inbox.application.actor import InboxActor
from src.modules.inbox.application.authorization import bao_dam_admin
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.repositories.channel_repository import IChannelRepository


class ListChannels:
    """Trả danh sách kênh cho trang quản trị.

    Entity ``Channel`` có ``encrypted_credential``; presentation chịu trách nhiệm
    không đưa trường đó ra response — use case không tự lộ token.
    """

    def __init__(self, channel_repo: IChannelRepository) -> None:
        self._channel_repo = channel_repo

    async def execute(self, actor: InboxActor, is_active: bool | None = None) -> list[Channel]:
        bao_dam_admin(actor)
        return await self._channel_repo.list_all(is_active=is_active)
