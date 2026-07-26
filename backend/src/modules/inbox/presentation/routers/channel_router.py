"""Endpoint quản lý kênh (Admin). Credential không bao giờ ra response."""

from uuid import UUID

from fastapi import APIRouter

from src.modules.inbox.application.use_cases.connect_channel import ConnectChannel
from src.modules.inbox.application.use_cases.deactivate_channel import DeactivateChannel
from src.modules.inbox.application.use_cases.list_channels import ListChannels
from src.modules.inbox.application.use_cases.update_channel import UpdateChannel
from src.modules.inbox.infrastructure.repositories.channel_repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.inbox.presentation.dependencies import (
    Actor,
    Cipher,
    Clock,
    DbSession,
    Directory,
)
from src.modules.inbox.presentation.schemas.channel_schemas import (
    ChannelResponse,
    ConnectChannelRequest,
    UpdateChannelRequest,
)

router = APIRouter(tags=["channels"])


@router.get("/channels", response_model=list[ChannelResponse])
async def liet_ke_kenh(
    actor: Actor, session: DbSession, is_active: bool | None = None
) -> list[ChannelResponse]:
    ds = await ListChannels(SqlAlchemyChannelRepository(session)).execute(
        actor=actor, is_active=is_active
    )
    return [ChannelResponse.from_entity(c) for c in ds]


@router.post("/channels", response_model=ChannelResponse, status_code=201)
async def ket_noi_kenh(
    du_lieu: ConnectChannelRequest,
    actor: Actor,
    session: DbSession,
    directory: Directory,
    cipher: Cipher,
    clock: Clock,
) -> ChannelResponse:
    ch = await ConnectChannel(
        channel_repo=SqlAlchemyChannelRepository(session),
        directory=directory,
        cipher=cipher,
        clock=clock,
    ).execute(
        actor=actor,
        platform=du_lieu.platform,
        external_channel_id=du_lieu.external_channel_id,
        name=du_lieu.name,
        credential=du_lieu.credential,
        department_id=du_lieu.department_id,
    )
    return ChannelResponse.from_entity(ch)


@router.patch("/channels/{channel_id}", response_model=ChannelResponse)
async def cap_nhat_kenh(
    channel_id: UUID,
    du_lieu: UpdateChannelRequest,
    actor: Actor,
    session: DbSession,
    directory: Directory,
    cipher: Cipher,
    clock: Clock,
) -> ChannelResponse:
    ch = await UpdateChannel(
        channel_repo=SqlAlchemyChannelRepository(session),
        directory=directory,
        cipher=cipher,
        clock=clock,
    ).execute(
        actor=actor,
        channel_id=channel_id,
        name=du_lieu.name,
        credential=du_lieu.credential,
        department_id=du_lieu.department_id,
        clear_department=du_lieu.clear_department,
    )
    return ChannelResponse.from_entity(ch)


@router.post("/channels/{channel_id}/deactivate", response_model=ChannelResponse)
async def ngat_kenh(
    channel_id: UUID, actor: Actor, session: DbSession, clock: Clock
) -> ChannelResponse:
    ch = await DeactivateChannel(
        channel_repo=SqlAlchemyChannelRepository(session), clock=clock
    ).execute(actor=actor, channel_id=channel_id)
    return ChannelResponse.from_entity(ch)
