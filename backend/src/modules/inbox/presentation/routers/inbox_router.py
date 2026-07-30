"""Endpoint inbox: liệt kê, xem, trả lời, phân, nhận, đóng hội thoại."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from src.modules.inbox.application.use_cases.assign_conversation_to_department import (
    AssignConversationToDepartment,
)
from src.modules.inbox.application.use_cases.close_conversation import CloseConversation
from src.modules.inbox.application.use_cases.get_conversation import GetConversation
from src.modules.inbox.application.use_cases.list_inbox import ListInbox
from src.modules.inbox.application.use_cases.reply_to_conversation import (
    ReplyToConversation,
)
from src.modules.inbox.application.use_cases.take_conversation import TakeConversation
from src.modules.inbox.domain.entities.conversation import ConversationStatus
from src.modules.inbox.domain.value_objects.message_content import MessageContent
from src.modules.inbox.infrastructure.repositories.channel_repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.inbox.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from src.modules.inbox.infrastructure.repositories.message_repository import (
    SqlAlchemyMessageRepository,
)
from src.modules.inbox.presentation.dependencies import (
    Actor,
    AttachmentStore,
    Cipher,
    Clock,
    DbSession,
    Directory,
    Notifier,
    Registry,
)
from src.modules.inbox.presentation.schemas.common import PageResponse
from src.modules.inbox.presentation.schemas.inbox_schemas import (
    AssignRequest,
    ConversationResponse,
    InboxItemResponse,
    MessageResponse,
    ReplyRequest,
)

router = APIRouter(tags=["inbox"])


@router.get("/inbox", response_model=PageResponse[InboxItemResponse])
async def liet_ke_inbox(
    actor: Actor,
    session: DbSession,
    status: ConversationStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[InboxItemResponse]:
    trang = await ListInbox(
        SqlAlchemyConversationRepository(session),
        SqlAlchemyCustomerRepository(session),
        SqlAlchemyChannelRepository(session),
    ).execute(actor=actor, status=status, limit=limit, offset=offset)
    return PageResponse(
        items=[InboxItemResponse.from_dto(i) for i in trang.items],
        total=trang.total,
        limit=trang.limit,
        offset=trang.offset,
    )


@router.get("/inbox/{conversation_id}", response_model=ConversationResponse)
async def xem_hoi_thoai(
    conversation_id: UUID,
    actor: Actor,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ConversationResponse:
    view = await GetConversation(
        SqlAlchemyConversationRepository(session),
        SqlAlchemyMessageRepository(session),
        SqlAlchemyChannelRepository(session),
        SqlAlchemyCustomerRepository(session),
    ).execute(actor=actor, conversation_id=conversation_id, limit=limit, offset=offset)
    return ConversationResponse.from_dto(view)


@router.post("/inbox/{conversation_id}/reply", response_model=MessageResponse)
async def tra_loi(
    conversation_id: UUID,
    du_lieu: ReplyRequest,
    actor: Actor,
    session: DbSession,
    registry: Registry,
    cipher: Cipher,
    store: AttachmentStore,
    notifier: Notifier,
    clock: Clock,
) -> MessageResponse:
    use_case = ReplyToConversation(
        conversation_repo=SqlAlchemyConversationRepository(session),
        channel_repo=SqlAlchemyChannelRepository(session),
        customer_repo=SqlAlchemyCustomerRepository(session),
        message_repo=SqlAlchemyMessageRepository(session),
        adapters=registry,
        cipher=cipher,
        attachment_store=store,
        notifier=notifier,
        clock=clock,
    )
    view = await use_case.execute(
        actor=actor,
        conversation_id=conversation_id,
        content=MessageContent(text=du_lieu.text),
    )
    return MessageResponse.from_dto(view)


async def _tra_ve_hoi_thoai(
    conversation_id: UUID, actor: Actor, session: DbSession
) -> ConversationResponse:
    view = await GetConversation(
        SqlAlchemyConversationRepository(session),
        SqlAlchemyMessageRepository(session),
        SqlAlchemyChannelRepository(session),
        SqlAlchemyCustomerRepository(session),
    ).execute(actor=actor, conversation_id=conversation_id)
    return ConversationResponse.from_dto(view)


@router.post("/inbox/{conversation_id}/assign", response_model=ConversationResponse)
async def phan_phong(
    conversation_id: UUID,
    du_lieu: AssignRequest,
    actor: Actor,
    session: DbSession,
    directory: Directory,
    notifier: Notifier,
    clock: Clock,
) -> ConversationResponse:
    await AssignConversationToDepartment(
        conversation_repo=SqlAlchemyConversationRepository(session),
        directory=directory,
        notifier=notifier,
        clock=clock,
    ).execute(actor=actor, conversation_id=conversation_id, department_id=du_lieu.department_id)
    return await _tra_ve_hoi_thoai(conversation_id, actor, session)


@router.post("/inbox/{conversation_id}/take", response_model=ConversationResponse)
async def nhan_hoi_thoai(
    conversation_id: UUID,
    actor: Actor,
    session: DbSession,
    notifier: Notifier,
    clock: Clock,
) -> ConversationResponse:
    await TakeConversation(
        conversation_repo=SqlAlchemyConversationRepository(session),
        notifier=notifier,
        clock=clock,
    ).execute(actor=actor, conversation_id=conversation_id)
    return await _tra_ve_hoi_thoai(conversation_id, actor, session)


@router.post("/inbox/{conversation_id}/close", response_model=ConversationResponse)
async def dong_hoi_thoai(
    conversation_id: UUID,
    actor: Actor,
    session: DbSession,
    notifier: Notifier,
    clock: Clock,
    request: Request,
) -> ConversationResponse:
    conversation = await CloseConversation(
        conversation_repo=SqlAlchemyConversationRepository(session),
        notifier=notifier,
        clock=clock,
    ).execute(actor=actor, conversation_id=conversation_id)
    phan_hoi = await _tra_ve_hoi_thoai(conversation_id, actor, session)

    # Nhân viên vừa rảnh ra → hook hạ nguồn (assignment #3) kéo hàng đợi phòng cho
    # người trong ca. Composition root đăng ký callable vào app.state; router chỉ
    # gọi (không import assignment — giữ inbox ⊥ assignment). Commit thao tác đóng
    # TRƯỚC khi chạy hook (dependency get_session commit khi request xong; nhưng
    # hook chạy trên session RIÊNG nên cần dữ liệu đã thấy được). Đóng đã ghi vào
    # session hiện tại; flush để hook (session khác) đọc được sau commit của nó.
    await session.commit()
    post_close_hooks = getattr(request.app.state, "post_close_hooks", ())
    for hook in post_close_hooks:
        await hook(conversation.department_id)

    return phan_hoi
