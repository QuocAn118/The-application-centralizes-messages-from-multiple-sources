"""Use case: Admin ngắt một kênh (ngừng nhận/gửi qua kênh đó)."""

from uuid import UUID

from src.modules.inbox.application.actor import InboxActor
from src.modules.inbox.application.authorization import bao_dam_admin
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.repositories.channel_repository import IChannelRepository
from src.shared.application.exceptions import NotFoundError
from src.shared.application.ports import IClock


class DeactivateChannel:
    """Đánh dấu một kênh ngừng hoạt động."""

    def __init__(self, channel_repo: IChannelRepository, clock: IClock) -> None:
        self._channel_repo = channel_repo
        self._clock = clock

    async def execute(self, actor: InboxActor, channel_id: UUID) -> Channel:
        bao_dam_admin(actor)

        channel = await self._channel_repo.get_by_id(channel_id)
        if channel is None:
            raise NotFoundError("Không tìm thấy kênh.", code="CHANNEL_NOT_FOUND")

        channel.deactivate(self._clock.now())
        await self._channel_repo.update(channel)
        return channel
