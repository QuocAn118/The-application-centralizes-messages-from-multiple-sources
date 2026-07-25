"""Use case: xem chi tiết một hội thoại kèm các tin của nó."""

from uuid import UUID

from src.modules.inbox.application.actor import InboxActor
from src.modules.inbox.application.authorization import bao_dam_thao_tac
from src.modules.inbox.application.dto.inbox_dto import (
    AttachmentView,
    ConversationView,
    MessageView,
)
from src.modules.inbox.domain.entities.message import Message
from src.modules.inbox.domain.repositories.channel_repository import IChannelRepository
from src.modules.inbox.domain.repositories.conversation_repository import (
    IConversationRepository,
)
from src.modules.inbox.domain.repositories.customer_repository import (
    ICustomerRepository,
)
from src.modules.inbox.domain.repositories.message_repository import IMessageRepository
from src.shared.application.exceptions import NotFoundError

GIOI_HAN_TIN_TOI_DA = 200


class GetConversation:
    """Đọc một hội thoại và lịch sử tin, trong phạm vi quyền người gọi."""

    def __init__(
        self,
        conversation_repo: IConversationRepository,
        message_repo: IMessageRepository,
        channel_repo: IChannelRepository,
        customer_repo: ICustomerRepository,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._channel_repo = channel_repo
        self._customer_repo = customer_repo

    async def execute(
        self,
        actor: InboxActor,
        conversation_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> ConversationView:
        conversation = await self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError("Không tìm thấy hội thoại.", code="CONVERSATION_NOT_FOUND")
        bao_dam_thao_tac(actor, conversation)

        channel = await self._channel_repo.get_by_id(conversation.channel_id)
        customer = await self._customer_repo.get_by_id(conversation.customer_id)
        if channel is None or customer is None:  # pragma: no cover - dữ liệu luôn nhất quán
            raise RuntimeError("Hội thoại trỏ tới kênh/khách không tồn tại.")

        gioi_han = min(max(limit, 1), GIOI_HAN_TIN_TOI_DA)
        vi_tri = max(offset, 0)
        messages = await self._message_repo.list_for_conversation(
            conversation.id, limit=gioi_han, offset=vi_tri
        )
        message_views = [await self._to_message_view(m) for m in messages]

        return ConversationView(
            conversation_id=conversation.id,
            channel_id=conversation.channel_id,
            platform=channel.platform,
            customer_id=conversation.customer_id,
            customer_display_name=customer.display_name,
            status=conversation.status,
            department_id=conversation.department_id,
            assigned_user_id=conversation.assigned_user_id,
            last_message_at=conversation.last_message_at,
            messages=tuple(message_views),
        )

    async def _to_message_view(self, message: Message) -> MessageView:
        attachments = await self._message_repo.list_attachments(message.id)
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
