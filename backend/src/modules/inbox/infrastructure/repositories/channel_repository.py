"""Repository kênh dùng SQLAlchemy."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.mappers.channel_mapper import ChannelMapper
from src.modules.inbox.infrastructure.models.channel_model import ChannelModel


class SqlAlchemyChannelRepository:
    """Truy xuất kênh từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lay_model(self, channel_id: UUID) -> ChannelModel | None:
        ket_qua = await self._session.execute(
            select(ChannelModel).where(ChannelModel.id == channel_id)
        )
        return ket_qua.scalar_one_or_none()

    async def get_by_id(self, channel_id: UUID) -> Channel | None:
        model = await self._lay_model(channel_id)
        return ChannelMapper.to_domain(model) if model else None

    async def get_by_external(self, platform: Platform, external_channel_id: str) -> Channel | None:
        ket_qua = await self._session.execute(
            select(ChannelModel).where(
                ChannelModel.platform == platform.value,
                ChannelModel.external_channel_id == external_channel_id,
            )
        )
        model = ket_qua.scalar_one_or_none()
        return ChannelMapper.to_domain(model) if model else None

    async def add(self, channel: Channel) -> None:
        self._session.add(ChannelMapper.to_model(channel))

    async def update(self, channel: Channel) -> None:
        model = await self._lay_model(channel.id)
        if model is None:
            raise ValueError(f"Không tìm thấy kênh {channel.id} để cập nhật.")
        ChannelMapper.update_model(model, channel)

    async def list_all(self, is_active: bool | None = None) -> list[Channel]:
        cau = select(ChannelModel)
        if is_active is not None:
            cau = cau.where(ChannelModel.is_active == is_active)
        cau = cau.order_by(ChannelModel.created_at)
        ket_qua = await self._session.execute(cau)
        return [ChannelMapper.to_domain(m) for m in ket_qua.scalars()]
