"""Router nhận webhook từ các nền tảng: ``POST /webhooks/{platform}``.

Luồng (spec §7): chọn adapter theo platform → verify chữ ký (sai → 403 không lộ
lý do) → với mỗi sự kiện: tải media qua adapter, rồi đưa vào IngestInboundMessage
(idempotent). Luôn trả 200 để nền tảng không gửi lại — kể cả event trùng.

GET cùng đường dẫn phục vụ bước Meta/Zalo verify webhook (hub.challenge).
"""

import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse

from src.modules.inbox.application.use_cases.ingest_inbound_message import (
    IngestInboundMessage,
)
from src.modules.inbox.domain.ports import IChannelAdapter, InboundEvent
from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.channels.errors import WebhookSignatureError
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
    AttachmentStore,
    Clock,
    DbSession,
    Registry,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


@router.get("/webhooks/{platform}")
async def verify_webhook(platform: Platform, request: Request) -> Response:
    """Meta/Zalo gọi GET kèm ``hub.challenge`` khi đăng ký webhook.

    Trả lại challenge nếu ``hub.verify_token`` khớp token cấu hình. Không có
    token cấu hình thì bỏ qua bước verify (dev).
    """
    params = request.query_params
    challenge = params.get("hub.challenge")
    verify_token = params.get("hub.verify_token")
    expected = getattr(request.app.state, "inbox_webhook_verify_token", None)
    if challenge is not None and (expected is None or verify_token == expected):
        return PlainTextResponse(challenge)
    return PlainTextResponse("", status_code=403)


@router.post("/webhooks/{platform}")
async def nhan_webhook(
    platform: Platform,
    request: Request,
    session: DbSession,
    registry: Registry,
    store: AttachmentStore,
    clock: Clock,
) -> Response:
    raw_body = await request.body()
    headers = dict(request.headers)

    adapter = registry.for_platform(platform)
    try:
        events = adapter.parse_webhook(raw_body, headers)
    except WebhookSignatureError:
        # Không lộ lý do (RB-3): chỉ 403.
        return Response(status_code=403)

    use_case = IngestInboundMessage(
        channel_repo=SqlAlchemyChannelRepository(session),
        customer_repo=SqlAlchemyCustomerRepository(session),
        conversation_repo=SqlAlchemyConversationRepository(session),
        message_repo=SqlAlchemyMessageRepository(session),
        attachment_store=store,
        notifier=request.app.state.inbox_notifier,
        clock=clock,
    )

    for event in events:
        raw_attachments = await _tai_dinh_kem(adapter, event)
        await use_case.execute(event, raw_attachments)

    # Luôn 200: nền tảng coi 2xx là "đã nhận", kể cả event trùng đã idempotent.
    return Response(status_code=200)


async def _tai_dinh_kem(adapter: IChannelAdapter, event: InboundEvent) -> list[bytes]:
    """Tải mọi tệp đính kèm của một sự kiện, giữ đúng thứ tự.

    Một tệp tải lỗi làm hỏng cả tin — nhưng ở #1 chấp nhận: thà 500 để nền tảng
    gửi lại còn hơn lưu tin thiếu ảnh âm thầm (RB-4).
    """
    return [await adapter.download_attachment(ref) for ref in event.content.attachments]
