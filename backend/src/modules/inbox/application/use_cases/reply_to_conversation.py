"""Use case: nhân viên trả lời một hội thoại.

Gửi tin ra nền tảng qua adapter (dùng credential đã giải mã của kênh) rồi lưu
lại tin đi. Tin chỉ được lưu sau khi gửi thành công — tránh ghi khống một tin
mà khách không nhận được.
"""

from uuid import UUID

from src.modules.inbox.application.actor import InboxActor
from src.modules.inbox.application.authorization import bao_dam_thao_tac
from src.modules.inbox.application.dto.inbox_dto import MessageView
from src.modules.inbox.domain.entities.message import Message
from src.modules.inbox.domain.ports import (
    CHANGE_NEW_MESSAGE,
    IChannelAdapterRegistry,
    ICredentialCipher,
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
from src.modules.inbox.domain.value_objects.message_content import MessageContent
from src.shared.application.exceptions import NotFoundError
from src.shared.application.ports import IClock


class ReplyToConversation:
    """Gửi một tin trả lời cho khách trong một hội thoại."""

    def __init__(
        self,
        conversation_repo: IConversationRepository,
        channel_repo: IChannelRepository,
        customer_repo: ICustomerRepository,
        message_repo: IMessageRepository,
        adapters: IChannelAdapterRegistry,
        cipher: ICredentialCipher,
        notifier: IRealtimeNotifier,
        clock: IClock,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._channel_repo = channel_repo
        self._customer_repo = customer_repo
        self._message_repo = message_repo
        self._adapters = adapters
        self._cipher = cipher
        self._notifier = notifier
        self._clock = clock

    async def execute(
        self, actor: InboxActor, conversation_id: UUID, content: MessageContent
    ) -> MessageView:
        conversation = await self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError("Không tìm thấy hội thoại.", code="CONVERSATION_NOT_FOUND")
        bao_dam_thao_tac(actor, conversation)

        channel = await self._channel_repo.get_by_id(conversation.channel_id)
        if channel is None:  # pragma: no cover - dữ liệu luôn nhất quán
            raise NotFoundError("Không tìm thấy kênh của hội thoại.", code="CHANNEL_NOT_FOUND")
        customer = await self._customer_repo.get_by_id(conversation.customer_id)
        if customer is None:  # pragma: no cover - dữ liệu luôn nhất quán
            raise NotFoundError("Không tìm thấy khách của hội thoại.", code="CUSTOMER_NOT_FOUND")

        # Adapter cần credential thô để gọi API; chỉ giải mã tại đây, không lưu lại.
        adapter = self._adapters.for_platform(channel.platform)
        await adapter.send_message(
            encrypted_credential=channel.encrypted_credential,
            external_customer_id=customer.external_id,
            content=content,
        )

        now = self._clock.now()
        message = Message.outbound(
            conversation_id=conversation.id,
            text=content.text,
            sender_user_id=actor.user_id,
            now=now,
        )
        await self._message_repo.add(message, [])

        conversation.updated_at = now
        conversation.last_message_at = now
        await self._conversation_repo.update(conversation)

        await self._notifier.notify_conversation_changed(
            conversation.id, conversation.department_id, CHANGE_NEW_MESSAGE
        )

        return MessageView(
            id=message.id,
            direction=message.direction,
            text=message.text,
            created_at=message.created_at,
            sender_user_id=message.sender_user_id,
        )
