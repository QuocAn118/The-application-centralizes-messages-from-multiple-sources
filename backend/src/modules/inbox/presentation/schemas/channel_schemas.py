"""Schema cho các endpoint quản lý kênh (Admin).

Điểm mấu chốt bảo mật: ``ChannelResponse`` **không** có trường credential —
token (dù đã mã hoá) không bao giờ ra khỏi API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.value_objects.platform import Platform


class ConnectChannelRequest(BaseModel):
    platform: Platform
    external_channel_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=200)
    credential: str = Field(min_length=1)
    department_id: UUID | None = None


class UpdateChannelRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    credential: str | None = Field(default=None, min_length=1)
    department_id: UUID | None = None
    clear_department: bool = False


class ChannelResponse(BaseModel):
    id: UUID
    platform: str
    external_channel_id: str
    name: str
    department_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, ch: Channel) -> "ChannelResponse":
        # Cố ý bỏ encrypted_credential — không lộ token ra response.
        return cls(
            id=ch.id,
            platform=ch.platform.value,
            external_channel_id=ch.external_channel_id,
            name=ch.name,
            department_id=ch.department_id,
            is_active=ch.is_active,
            created_at=ch.created_at,
            updated_at=ch.updated_at,
        )
