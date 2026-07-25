"""Entity tin nhắn trong một hội thoại."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from src.modules.inbox.domain.value_objects.message_content import MessageContent
from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import BusinessRuleViolationError


class MessageDirection(StrEnum):
    """Chiều của tin: từ khách vào, hay từ nhân viên ra."""

    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class InboundNeedsExternalIdError(BusinessRuleViolationError):
    """Tin đến bắt buộc có mã tin của nền tảng để chống trùng."""

    def __init__(self) -> None:
        super().__init__(
            "Tin đến phải kèm mã tin của nền tảng (dùng để chống xử lý trùng).",
            code="INBOUND_NEEDS_EXTERNAL_ID",
        )


class OutboundNeedsSenderError(BusinessRuleViolationError):
    """Tin đi bắt buộc biết nhân viên nào gửi."""

    def __init__(self) -> None:
        super().__init__(
            "Tin đi phải biết nhân viên nào gửi.",
            code="OUTBOUND_NEEDS_SENDER",
        )


@dataclass(eq=False, kw_only=True)
class Message(AggregateRoot):
    """Một tin trong hội thoại.

    Nội dung text lưu trực tiếp; tệp đính kèm là các ``Attachment`` riêng trỏ
    về tin này. ``external_message_id`` chỉ có ở tin đến và là chốt để không
    xử lý trùng khi nền tảng gửi lại webhook. ``sender_user_id`` chỉ có ở tin
    đi (UUID tham chiếu identity, không phải khoá ngoại).
    """

    conversation_id: UUID
    direction: MessageDirection
    created_at: datetime
    text: str | None = None
    external_message_id: str | None = None
    sender_user_id: UUID | None = None

    @classmethod
    def inbound(
        cls,
        conversation_id: UUID,
        content: MessageContent,
        external_message_id: str,
        now: datetime,
    ) -> "Message":
        """Tin từ khách gửi vào.

        Nhận nguyên ``MessageContent`` (đã tự chặn nội dung rỗng) nên bất biến
        'tin phải có text hoặc đính kèm' được giữ ở một chỗ; entity chỉ trích
        ``text`` ra lưu, các đính kèm là ``Attachment`` riêng trỏ về tin này.
        """
        if not external_message_id.strip():
            raise InboundNeedsExternalIdError
        return cls(
            conversation_id=conversation_id,
            direction=MessageDirection.INBOUND,
            text=content.text,
            external_message_id=external_message_id,
            sender_user_id=None,
            created_at=now,
        )

    @classmethod
    def outbound(
        cls,
        conversation_id: UUID,
        content: MessageContent,
        sender_user_id: UUID,
        now: datetime,
    ) -> "Message":
        """Tin nhân viên gửi ra."""
        if sender_user_id is None:
            raise OutboundNeedsSenderError
        return cls(
            conversation_id=conversation_id,
            direction=MessageDirection.OUTBOUND,
            text=content.text,
            external_message_id=None,
            sender_user_id=sender_user_id,
            created_at=now,
        )
