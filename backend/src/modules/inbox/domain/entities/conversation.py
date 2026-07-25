"""Entity hội thoại — luồng tin giữa một khách và một kênh."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import BusinessRuleViolationError


class ConversationStatus(StrEnum):
    """Trạng thái vòng đời hội thoại.

    ``CHO_PHAN``: chưa thuộc phòng nào — chờ Manager phân (ở #3 sẽ do AI phân).
    ``DANG_MO``: đã thuộc một phòng, đang chờ hoặc đang được xử lý.
    ``DA_DONG``: nhân viên đã đánh dấu xử lý xong; tin mới của khách mở lại.
    """

    CHO_PHAN = "CHO_PHAN"
    DANG_MO = "DANG_MO"
    DA_DONG = "DA_DONG"


class NotAwaitingAssignmentError(BusinessRuleViolationError):
    """Chỉ hội thoại đang chờ phân mới được phân về phòng."""

    def __init__(self) -> None:
        super().__init__(
            "Hội thoại này không ở trạng thái chờ phân.",
            code="NOT_AWAITING_ASSIGNMENT",
        )


class NotOpenError(BusinessRuleViolationError):
    """Thao tác này chỉ hợp lệ khi hội thoại đang mở."""

    def __init__(self) -> None:
        super().__init__(
            "Hội thoại phải đang mở (đã thuộc một phòng) mới thực hiện được thao tác này.",
            code="CONVERSATION_NOT_OPEN",
        )


class AlreadyAssignedError(BusinessRuleViolationError):
    """Hội thoại đã có người xử lý."""

    def __init__(self) -> None:
        super().__init__(
            "Hội thoại này đã có người nhận xử lý.",
            code="CONVERSATION_ALREADY_ASSIGNED",
        )


@dataclass(eq=False, kw_only=True)
class Conversation(AggregateRoot):
    """Một hội thoại gắn với đúng một cặp (kênh, khách).

    ``department_id`` và ``assigned_user_id`` là tham chiếu UUID sang identity,
    cố ý không phải khoá ngoại — giữ module inbox độc lập. Đây cũng chính là
    hai chỗ mà sub-project #3 (auto-assignment) sẽ điền tự động thay cho việc
    Manager phân tay và nhân viên tự nhận ở #1.
    """

    channel_id: UUID
    customer_id: UUID
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    department_id: UUID | None = None
    assigned_user_id: UUID | None = None

    @classmethod
    def start(
        cls,
        channel_id: UUID,
        customer_id: UUID,
        department_id: UUID | None,
        now: datetime,
    ) -> "Conversation":
        """Mở một hội thoại mới.

        Nếu kênh đã gắn phòng thì hội thoại vào ``DANG_MO`` ngay; nếu chưa,
        rơi vào ``CHO_PHAN`` để Manager phân.
        """
        trang_thai = (
            ConversationStatus.DANG_MO if department_id is not None else ConversationStatus.CHO_PHAN
        )
        return cls(
            channel_id=channel_id,
            customer_id=customer_id,
            department_id=department_id,
            assigned_user_id=None,
            status=trang_thai,
            created_at=now,
            updated_at=now,
            last_message_at=now,
        )

    def assign_to_department(self, department_id: UUID, now: datetime) -> None:
        """Manager phân hội thoại đang chờ về một phòng."""
        if self.status is not ConversationStatus.CHO_PHAN:
            raise NotAwaitingAssignmentError
        self.department_id = department_id
        self.status = ConversationStatus.DANG_MO
        self.updated_at = now

    def assign_to_agent(self, user_id: UUID, now: datetime) -> None:
        """Nhân viên nhận hội thoại (hoặc được giao)."""
        if self.status is not ConversationStatus.DANG_MO:
            raise NotOpenError
        if self.assigned_user_id is not None:
            raise AlreadyAssignedError
        self.assigned_user_id = user_id
        self.updated_at = now

    def close(self, now: datetime) -> None:
        """Đánh dấu đã xử lý xong."""
        if self.status is not ConversationStatus.DANG_MO:
            raise NotOpenError
        self.status = ConversationStatus.DA_DONG
        self.updated_at = now

    def register_incoming(self, now: datetime) -> None:
        """Ghi nhận có tin đến. Nếu đang đóng thì mở lại; giữ nguyên người đã gán."""
        if self.status is ConversationStatus.DA_DONG:
            self.status = ConversationStatus.DANG_MO
        self.last_message_at = now
        self.updated_at = now
