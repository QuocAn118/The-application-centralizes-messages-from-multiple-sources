"""Use case: nhân viên trả lời một hội thoại.

Gửi tin ra nền tảng qua adapter (dùng credential đã giải mã của kênh) rồi lưu
lại tin đi cùng các tệp đính kèm. Tin chỉ được lưu sau khi gửi thành công —
tránh ghi khống một tin mà khách không nhận được.
"""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from src.modules.inbox.application.actor import InboxActor
from src.modules.inbox.application.authorization import bao_dam_thao_tac
from src.modules.inbox.application.dto.inbox_dto import AttachmentView, MessageView
from src.modules.inbox.domain.entities.attachment import Attachment
from src.modules.inbox.domain.entities.conversation import ConversationStatus, NotOpenError
from src.modules.inbox.domain.entities.message import Message
from src.modules.inbox.domain.ports import (
    CHANGE_NEW_MESSAGE,
    IAttachmentStore,
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
from src.modules.inbox.domain.value_objects.message_content import AttachmentRef, MessageContent
from src.shared.application.exceptions import ConflictError, NotFoundError
from src.shared.application.ports import IClock


class ChannelInactiveError(ConflictError):
    """Không gửi được qua một kênh đã ngừng hoạt động."""

    def __init__(self) -> None:
        super().__init__(
            "Kênh của hội thoại này đã ngừng hoạt động, không gửi được tin.",
            code="CHANNEL_INACTIVE",
        )


class ReplyToConversation:
    """Gửi một tin trả lời cho khách trong một hội thoại.

    Chỉ hợp lệ khi hội thoại đang mở (``DANG_MO``): hội thoại chờ-phân phải được
    phân về phòng trước, hội thoại đã đóng phải được mở lại có chủ đích — cùng
    một quy tắc máy trạng thái, không lách qua đường trả lời.
    """

    def __init__(
        self,
        conversation_repo: IConversationRepository,
        channel_repo: IChannelRepository,
        customer_repo: ICustomerRepository,
        message_repo: IMessageRepository,
        adapters: IChannelAdapterRegistry,
        cipher: ICredentialCipher,
        attachment_store: IAttachmentStore,
        notifier: IRealtimeNotifier,
        clock: IClock,
        public_url: Callable[[UUID, UUID], str] | None = None,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._channel_repo = channel_repo
        self._customer_repo = customer_repo
        self._message_repo = message_repo
        self._adapters = adapters
        self._cipher = cipher
        self._attachment_store = attachment_store
        self._notifier = notifier
        self._clock = clock
        # Sinh URL công khai cho một tệp đã lưu: (attachment_id, conversation_id)
        # → URL. Nền tảng tự tải ảnh từ đó. ``None`` = không gửi kèm ảnh được
        # (giữ tương thích với nơi gọi cũ chỉ dùng text).
        self._public_url = public_url

    async def execute(
        self,
        actor: InboxActor,
        conversation_id: UUID,
        content: MessageContent,
        raw_attachments: list[bytes] | None = None,
    ) -> MessageView:
        """Gửi và lưu một tin trả lời.

        ``raw_attachments`` là nội dung tệp nhân viên gửi kèm (thứ tự trùng với
        ``content.attachments``); router đọc từ upload rồi đưa vào để use case
        không tự chạm I/O tệp.
        """
        raw = raw_attachments or []

        conversation = await self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError("Không tìm thấy hội thoại.", code="CONVERSATION_NOT_FOUND")
        bao_dam_thao_tac(actor, conversation)
        if conversation.status is not ConversationStatus.DANG_MO:
            raise NotOpenError

        if len(raw) != len(content.attachments):
            raise ValueError("Số tệp gửi lên không khớp số tham chiếu đính kèm.")

        channel = await self._channel_repo.get_by_id(conversation.channel_id)
        if channel is None:  # pragma: no cover - dữ liệu luôn nhất quán
            raise NotFoundError("Không tìm thấy kênh của hội thoại.", code="CHANNEL_NOT_FOUND")
        if not channel.is_active:
            raise ChannelInactiveError
        customer = await self._customer_repo.get_by_id(conversation.customer_id)
        if customer is None:  # pragma: no cover - dữ liệu luôn nhất quán
            raise NotFoundError("Không tìm thấy khách của hội thoại.", code="CUSTOMER_NOT_FOUND")

        now = self._clock.now()
        message = Message.outbound(
            conversation_id=conversation.id,
            content=content,
            sender_user_id=actor.user_id,
            now=now,
        )

        # Lưu tệp TRƯỚC khi gửi: Zalo/Meta không nhận nội dung tệp trực tiếp mà
        # tự tải về từ một URL ta cung cấp, nên phải có tệp trên đĩa và có URL
        # công khai rồi mới gọi được adapter.
        attachments = await self._luu_dinh_kem(content, raw, message.id, now)

        noi_dung_gui = content
        if attachments and self._public_url is not None:
            noi_dung_gui = MessageContent(
                text=content.text,
                attachments=tuple(
                    AttachmentRef(
                        kind=a.kind,
                        url=self._public_url(a.id, conversation.id),
                        content_type=a.content_type,
                    )
                    for a in attachments
                ),
            )

        # Adapter cần token thô để gọi API; giải mã tại đây, không lưu lại bản thô.
        adapter = self._adapters.for_platform(channel.platform)
        access_token = self._cipher.decrypt(channel.encrypted_credential)
        await adapter.send_message(
            access_token=access_token,
            external_customer_id=customer.external_id,
            content=noi_dung_gui,
        )

        await self._message_repo.add(message, attachments)

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

    async def _luu_dinh_kem(
        self,
        content: MessageContent,
        raw_attachments: list[bytes],
        message_id: UUID,
        now: datetime,
    ) -> list[Attachment]:
        # Cũng như tin đến: đính kèm gửi đi phải được lưu lại để lịch sử hội
        # thoại không mất ảnh (RB-4). strict=True để lệch số lượng nổ ngay.
        stored: list[Attachment] = []
        for ref, data in zip(content.attachments, raw_attachments, strict=True):
            info = await self._attachment_store.save(data, _ten_goi_y(ref), ref.content_type)
            stored.append(
                Attachment.stored(
                    message_id=message_id,
                    kind=ref.kind,
                    stored_path=info.stored_path,
                    now=now,
                    original_url=ref.url or None,
                    content_type=info.content_type,
                    size=info.size,
                )
            )
        return stored


def _ten_goi_y(ref: AttachmentRef) -> str:
    """Tên gợi ý để store lưu; store toàn quyền quyết định tên cuối.

    Ảnh nhân viên tải lên chưa có URL nền tảng (``url`` rỗng), nên rơi về tên
    mặc định — store vẫn gắn tiền tố UUID nên không đè nhau.
    """
    duoi = ref.url.rsplit("/", 1)[-1] if ref.url else ""
    return duoi or "attachment"
