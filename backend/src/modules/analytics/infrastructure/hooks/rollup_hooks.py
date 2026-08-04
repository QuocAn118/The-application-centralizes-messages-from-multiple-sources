"""Hook incremental của #5 — dịch sự kiện #1 sang ``ApplyEventDelta``.

Composition root đăng ký các hook này vào ``app.state`` (``post_ingest_hooks``,
``post_close_hooks``, ``post_reply_hooks``). Router của inbox chỉ gọi callable —
KHÔNG import analytics (giữ #1 ⊥ #5). Hook thuộc ``analytics.infrastructure`` nên
được phép biết cả inbox lẫn use case analytics.

Hai hợp đồng chốt ở review (bắt buộc để incremental khớp backfill):
- **Phòng HIỆN TẠI** (GĐ3 F-A): đọc ``conversation.department_id`` hiện tại của hội
  thoại khi ghi — kể cả INBOUND (đừng ghi NULL lúc CHO_PHAN).
- **Event-time theo tz** (GĐ2): ``work_date`` = ngày địa phương (``app_timezone``)
  của thời điểm sự kiện.

An toàn: mỗi hook chạy trên **session riêng**, SAU khi #1 commit; **nuốt mọi lỗi**
(rollup lỗi không được làm hỏng luồng chính — RB-1). ``RebuildDailyRollup`` sửa lệch.

NỢ: ``assigned_count`` chưa có hook (thiếu điểm móc sạch + ``assignment_log`` #3) →
bản đầu ``assigned_count`` = 0. Nối khi có assignment_log.
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.analytics.application.use_cases.apply_event_delta import (
    ApplyEventDelta,
    EventContext,
)
from src.modules.analytics.domain.ports import EventKind
from src.modules.inbox.domain.entities.message import MessageDirection
from src.modules.inbox.domain.ports import ClosedConversation, InboundEvent
from src.modules.inbox.infrastructure.models.channel_model import ChannelModel
from src.modules.inbox.infrastructure.models.conversation_model import ConversationModel
from src.modules.inbox.infrastructure.models.message_model import MessageModel
from src.modules.keyword.infrastructure.inbox_bridge.conversation_directory import (
    InboxConversationDirectory,
)

logger = logging.getLogger(__name__)

type _SessionProvider = Callable[[], async_sessionmaker[AsyncSession]]
type _ApplyFactory = Callable[[AsyncSession], ApplyEventDelta]


async def _phong_va_kenh(session: AsyncSession, conversation_id: UUID) -> tuple[UUID | None, str]:
    """Phòng HIỆN TẠI + nền tảng kênh của hội thoại (rỗng nếu không thấy)."""
    cau = (
        select(ConversationModel.department_id, ChannelModel.platform)
        .join(ChannelModel, ChannelModel.id == ConversationModel.channel_id)
        .where(ConversationModel.id == conversation_id)
    )
    row = (await session.execute(cau)).first()
    if row is None:
        return None, ""
    return row[0], row[1]


def make_post_ingest_hook(
    session_provider: _SessionProvider, apply_factory: _ApplyFactory, timezone: str
) -> Callable[[InboundEvent], Awaitable[None]]:
    """Tin khách mới → +1 inbound cho (ngày tin, phòng hiện tại, kênh)."""
    tz = ZoneInfo(timezone)

    async def hook(event: InboundEvent) -> None:
        try:
            async with session_provider()() as session:
                conversation_id = await InboxConversationDirectory(session).resolve_conversation_id(
                    event.platform, event.external_channel_id, event.external_customer_id
                )
                if conversation_id is None:
                    return
                dept, platform = await _phong_va_kenh(session, conversation_id)
                # Event-time = created_at của tin INBOUND mới nhất (khớp backfill vốn
                # đọc message.created_at). InboundEvent không mang mốc thời gian.
                tin_luc = await session.scalar(
                    select(func.max(MessageModel.created_at)).where(
                        MessageModel.conversation_id == conversation_id,
                        MessageModel.direction == MessageDirection.INBOUND.value,
                    )
                )
                if tin_luc is None:
                    return
                ngay = tin_luc.astimezone(tz).date()
                await apply_factory(session).execute(
                    EventKind.INBOUND,
                    EventContext(work_date=ngay, channel_platform=platform, department_id=dept),
                )
                await session.commit()
        except Exception:
            logger.exception("Hook rollup inbound lỗi — bỏ qua")

    return hook


def make_post_reply_hook(
    session_provider: _SessionProvider, apply_factory: _ApplyFactory, timezone: str
) -> Callable[[UUID, UUID, datetime], Awaitable[None]]:
    """Nhân viên trả lời → +1 outbound; nếu là tin trả lời ĐẦU thì +1 mẫu first_response.

    Nhận ``(conversation_id, user_id, occurred_at)``. Tính first_response = giây từ
    tin INBOUND đầu tới tin OUTBOUND này, CHỈ khi đây là tin OUTBOUND đầu tiên của
    hội thoại (đếm outbound == 1 sau khi #1 đã lưu tin).
    """
    tz = ZoneInfo(timezone)

    async def hook(conversation_id: UUID, user_id: UUID, occurred_at: datetime) -> None:
        try:
            async with session_provider()() as session:
                dept, platform = await _phong_va_kenh(session, conversation_id)
                ngay = occurred_at.astimezone(tz).date()

                # first_response chỉ cho tin trả lời ĐẦU: đếm OUTBOUND của hội thoại.
                so_outbound = await session.scalar(
                    select(func.count())
                    .select_from(MessageModel)
                    .where(
                        MessageModel.conversation_id == conversation_id,
                        MessageModel.direction == MessageDirection.OUTBOUND.value,
                    )
                )
                seconds: int | None = None
                if so_outbound == 1:
                    tin_khach_dau = await session.scalar(
                        select(func.min(MessageModel.created_at)).where(
                            MessageModel.conversation_id == conversation_id,
                            MessageModel.direction == MessageDirection.INBOUND.value,
                        )
                    )
                    if tin_khach_dau is not None:
                        delta = int((occurred_at - tin_khach_dau).total_seconds())
                        if delta >= 0:
                            seconds = delta

                await apply_factory(session).execute(
                    EventKind.OUTBOUND,
                    EventContext(
                        work_date=ngay,
                        channel_platform=platform,
                        department_id=dept,
                        user_id=user_id,
                        seconds=seconds,
                    ),
                )
                await session.commit()
        except Exception:
            logger.exception("Hook rollup outbound lỗi — bỏ qua")

    return hook


def make_post_close_hook(
    session_provider: _SessionProvider, apply_factory: _ApplyFactory, timezone: str
) -> Callable[[ClosedConversation], Awaitable[None]]:
    """Đóng hội thoại → +1 closed (khối lượng) và +1 handled + mẫu resolution cho
    người nhận (nếu có).

    Nhận ``ClosedConversation`` (payload chung post-close). resolution = giây từ khi
    tạo hội thoại tới lúc đóng. Phòng lấy HIỆN TẠI của hội thoại (khớp backfill).
    """
    tz = ZoneInfo(timezone)

    async def hook(closed: ClosedConversation) -> None:
        try:
            async with session_provider()() as session:
                dept, platform = await _phong_va_kenh(session, closed.conversation_id)
                ngay = closed.closed_at.astimezone(tz).date()
                tao_luc = await session.scalar(
                    select(ConversationModel.created_at).where(
                        ConversationModel.id == closed.conversation_id
                    )
                )
                seconds: int | None = None
                if tao_luc is not None:
                    delta = int((closed.closed_at - tao_luc).total_seconds())
                    if delta >= 0:
                        seconds = delta
                await apply_factory(session).execute(
                    EventKind.CLOSED,
                    EventContext(
                        work_date=ngay,
                        channel_platform=platform,
                        department_id=dept,
                        user_id=closed.assigned_user_id,
                        seconds=seconds,
                    ),
                )
                await session.commit()
        except Exception:
            logger.exception("Hook rollup closed lỗi — bỏ qua")

    return hook
