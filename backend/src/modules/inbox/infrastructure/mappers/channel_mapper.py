"""Chuyển đổi giữa ORM model và domain entity của kênh."""

from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.models.channel_model import ChannelModel


class ChannelMapper:
    """Cầu nối giữa bảng ``channels`` và entity ``Channel``."""

    @staticmethod
    def to_domain(model: ChannelModel) -> Channel:
        return Channel(
            id=model.id,
            platform=Platform(model.platform),
            external_channel_id=model.external_channel_id,
            name=model.name,
            encrypted_credential=model.credential,
            department_id=model.department_id,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: Channel) -> ChannelModel:
        return ChannelModel(
            id=entity.id,
            platform=entity.platform.value,
            external_channel_id=entity.external_channel_id,
            name=entity.name,
            credential=entity.encrypted_credential,
            department_id=entity.department_id,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def update_model(model: ChannelModel, entity: Channel) -> None:
        model.name = entity.name
        model.credential = entity.encrypted_credential
        model.department_id = entity.department_id
        model.is_active = entity.is_active
        model.updated_at = entity.updated_at
