"""Use case: đưa một tin đến (đã chuẩn hoá từ webhook) vào inbox.

Đây là nơi luồng nhận tin hợp lại: tra kênh, tìm/tạo khách, tìm/mở hội thoại,
chống trùng, lưu tệp đính kèm đã tải về, lưu tin, rồi báo realtime. Adapter đã
xác minh chữ ký và chuẩn hoá payload thành ``InboundEvent`` trước khi tới đây —
use case này không biết gì về định dạng riêng của Zalo hay Meta.
"""

from datetime import datetime
from uuid import UUID

from src.modules.inbox.application.dto.inbox_dto import AttachmentView, MessageView
from src.modules.inbox.domain.entities.attachment import Attachment
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.entities.conversation import Conversation
from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.domain.entities.message import Message
from src.modules.inbox.domain.ports import (
    CHANGE_NEW_MESSAGE,
    IAttachmentStore,
    InboundEvent,
    IRealtimeNotifier,
)
from src.modules.inbox.domain.repositories.channel_repository import IChannelRepository
from src.modules.inbox.domain.repositories.conversation_repository import (
    IConversationRepository,
)
from src.modules.inbox.domain.repositories.customer_repository import (
    ICustomerRepository,
)
from src.modules.inbox.domain.repositories.message_repository import IMessageRepository
from src.modules.inbox.domain.value_objects.message_content import AttachmentRef
from src.shared.application.ports import IClock


class IngestInboundMessage:
    """Ghi nhận một tin từ khách vào hệ thống.

    Idempotent theo ``external_message_id``: nền tảng có thể gửi lại cùng một
    webhook, nên tin đã xử lý thì bỏ qua, không tạo bản trùng.
    """

    def __init__(
        self,
        channel_repo: IChannelRepository,
        customer_repo: ICustomerRepository,
        conversation_repo: IConversationRepository,
        message_repo: IMessageRepository,
        attachment_store: IAttachmentStore,
        notifier: IRealtimeNotifier,
        clock: IClock,
    ) -> None:
        self._channel_repo = channel_repo
        self._customer_repo = customer_repo
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._attachment_store = attachment_store
        self._notifier = notifier
        self._clock = clock

    async def execute(
        self, event: InboundEvent, raw_attachments: list[bytes]
    ) -> MessageView | None:
        """Xử lý một sự kiện đến.

        ``raw_attachments`` là nội dung tệp đã tải sẵn (theo thứ tự trùng với
        ``event.content.attachments``) — router tải qua adapter rồi đưa vào để
        use case không tự chạm mạng. Trả ``None`` nếu tin đã được xử lý trước đó.
        """
        if await self._message_repo.exists_external(event.external_message_id):
            return None

        channel = await self._channel_repo.get_by_external(
            event.platform, event.external_channel_id
        )
        if channel is None:
            # Webhook trỏ tới kênh chưa kết nối: bỏ qua lặng lẽ, không dựng dữ liệu mồ côi.
            return None

        now = self._clock.now()
        customer = await self._tim_hoac_tao_khach(channel.id, event, now)
        conversation = await self._tim_hoac_mo_hoi_thoai(channel, customer.id, now)

        message = Message.inbound(
            conversation_id=conversation.id,
            text=event.content.text,
            external_message_id=event.external_message_id,
            now=now,
        )
        attachments = await self._luu_dinh_kem(event, raw_attachments, message.id, now)
        await self._message_repo.add(message, attachments)

        await self._notifier.notify_conversation_changed(
            conversation.id, conversation.department_id, CHANGE_NEW_MESSAGE
        )

        return _to_view(message, attachments)

    async def _tim_hoac_tao_khach(
        self, channel_id: UUID, event: InboundEvent, now: datetime
    ) -> Customer:
        customer = await self._customer_repo.get_by_external(channel_id, event.external_customer_id)
        if customer is None:
            customer = Customer.register(
                channel_id=channel_id,
                platform=event.platform,
                external_id=event.external_customer_id,
                display_name=event.customer_display_name,
                now=now,
            )
            await self._customer_repo.add(customer)
        elif event.customer_display_name is not None:
            customer.update_profile(
                display_name=event.customer_display_name, avatar_url=None, now=now
            )
            await self._customer_repo.update(customer)
        return customer

    async def _tim_hoac_mo_hoi_thoai(
        self, channel: Channel, customer_id: UUID, now: datetime
    ) -> Conversation:
        conversation = await self._conversation_repo.get_open_for(channel.id, customer_id)
        if conversation is None:
            conversation = Conversation.start(
                channel_id=channel.id,
                customer_id=customer_id,
                department_id=channel.department_id,
                now=now,
            )
            await self._conversation_repo.add(conversation)
        else:
            conversation.register_incoming(now)
            await self._conversation_repo.update(conversation)
        return conversation

    async def _luu_dinh_kem(
        self,
        event: InboundEvent,
        raw_attachments: list[bytes],
        message_id: UUID,
        now: datetime,
    ) -> list[Attachment]:
        stored: list[Attachment] = []
        # strict=True: router phải tải đủ mọi attachment; lệch số lượng là lỗi
        # lập trình, phải nổ ngay chứ không âm thầm mất ảnh (xem RB-4).
        for ref, data in zip(event.content.attachments, raw_attachments, strict=True):
            info = await self._attachment_store.save(data, _ten_goi_y(ref), ref.content_type)
            stored.append(
                Attachment.stored(
                    message_id=message_id,
                    kind=ref.kind,
                    stored_path=info.stored_path,
                    now=now,
                    original_url=ref.url,
                    content_type=info.content_type,
                    size=info.size,
                )
            )
        return stored


def _ten_goi_y(ref: AttachmentRef) -> str:
    """Tên gợi ý để store lưu; store toàn quyền quyết định tên cuối."""
    duoi = ref.url.rsplit("/", 1)[-1]
    return duoi or "attachment"


def _to_view(message: Message, attachments: list[Attachment]) -> MessageView:
    return MessageView(
        id=message.id,
        direction=message.direction,
        text=message.text,
        created_at=message.created_at,
        sender_user_id=message.sender_user_id,
        attachments=tuple(
            AttachmentView(
                id=a.id,
                kind=a.kind,
                stored_path=a.stored_path,
                content_type=a.content_type,
                size=a.size,
            )
            for a in attachments
        ),
    )
