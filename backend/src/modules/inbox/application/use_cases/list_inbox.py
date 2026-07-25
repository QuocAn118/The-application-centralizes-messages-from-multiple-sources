"""Use case: liệt kê inbox theo phạm vi quyền của người gọi.

- Admin: thấy mọi hội thoại, kể cả chờ-phân.
- Manager: thấy hội thoại phòng mình và cả mục chờ-phân (để còn phân).
- Staff: chỉ hội thoại phòng mình, không thấy chờ-phân.

Bộ lọc phạm vi được ép ở đây, người gọi không tự nới rộng được.
"""

from dataclasses import dataclass
from uuid import UUID

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.dto.inbox_dto import InboxItem, Page
from src.modules.inbox.domain.entities.conversation import Conversation, ConversationStatus
from src.modules.inbox.domain.repositories.channel_repository import IChannelRepository
from src.modules.inbox.domain.repositories.conversation_repository import (
    IConversationRepository,
)
from src.modules.inbox.domain.repositories.customer_repository import (
    ICustomerRepository,
)

GIOI_HAN_TOI_DA = 100


@dataclass(frozen=True)
class _PhamVi:
    """Phạm vi truy vấn đã suy ra từ vai trò người gọi."""

    department_ids: list[UUID] | None
    include_awaiting: bool


def pham_vi_cua(actor: InboxActor) -> _PhamVi:
    """Suy ra phạm vi phòng ban + có gộp chờ-phân không, từ vai trò."""
    if actor.role is ActorRole.ADMIN:
        return _PhamVi(department_ids=None, include_awaiting=True)
    # Manager/Staff không có phòng thì không thấy gì thuộc phòng.
    department_ids = [actor.department_id] if actor.department_id is not None else []
    include_awaiting = actor.role is ActorRole.MANAGER
    return _PhamVi(department_ids=department_ids, include_awaiting=include_awaiting)


class ListInbox:
    """Trả một trang inbox trong phạm vi quyền người gọi."""

    def __init__(
        self,
        conversation_repo: IConversationRepository,
        customer_repo: ICustomerRepository,
        channel_repo: IChannelRepository,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._customer_repo = customer_repo
        self._channel_repo = channel_repo

    async def execute(
        self,
        actor: InboxActor,
        status: ConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[InboxItem]:
        pv = pham_vi_cua(actor)
        gioi_han = min(max(limit, 1), GIOI_HAN_TOI_DA)
        vi_tri = max(offset, 0)

        conversations = await self._conversation_repo.list_for_scope(
            department_ids=pv.department_ids,
            include_awaiting=pv.include_awaiting,
            status=status,
            limit=gioi_han,
            offset=vi_tri,
        )
        tong = await self._conversation_repo.count_for_scope(
            department_ids=pv.department_ids,
            include_awaiting=pv.include_awaiting,
            status=status,
        )
        items = [await self._to_item(c) for c in conversations]
        return Page(items=items, total=tong, limit=gioi_han, offset=vi_tri)

    async def _to_item(self, conversation: Conversation) -> InboxItem:
        channel = await self._channel_repo.get_by_id(conversation.channel_id)
        customer = await self._customer_repo.get_by_id(conversation.customer_id)
        if channel is None or customer is None:  # pragma: no cover - dữ liệu luôn nhất quán
            raise RuntimeError("Hội thoại trỏ tới kênh/khách không tồn tại.")
        return InboxItem(
            conversation_id=conversation.id,
            channel_id=conversation.channel_id,
            platform=channel.platform,
            customer_id=conversation.customer_id,
            customer_display_name=customer.display_name,
            status=conversation.status,
            department_id=conversation.department_id,
            assigned_user_id=conversation.assigned_user_id,
            last_message_at=conversation.last_message_at,
        )
