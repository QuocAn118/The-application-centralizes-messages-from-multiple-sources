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
from src.modules.inbox.domain.repositories.message_repository import IMessageRepository

GIOI_HAN_TOI_DA = 100

# Dòng preview chỉ hiện một dòng trên giao diện; cắt ở đây để không đẩy cả tin
# 8000 ký tự qua mạng cho mỗi dòng danh sách.
DAI_PREVIEW = 120


def _rut_gon(text: str | None) -> str | None:
    """Gộp khoảng trắng và cắt ngắn nội dung preview."""
    if text is None:
        return None
    gon = " ".join(text.split())
    if not gon:
        return None
    return gon if len(gon) <= DAI_PREVIEW else gon[:DAI_PREVIEW].rstrip() + "…"


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
        message_repo: IMessageRepository | None = None,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._customer_repo = customer_repo
        self._channel_repo = channel_repo
        # Tuỳ chọn: không có thì danh sách vẫn chạy, chỉ thiếu dòng preview.
        self._message_repo = message_repo

    async def execute(
        self,
        actor: InboxActor,
        status: ConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
        q: str | None = None,
    ) -> Page[InboxItem]:
        """``q`` lọc thêm theo tên khách hiển thị; phạm vi quyền vẫn được ép trước."""
        pv = pham_vi_cua(actor)
        gioi_han = min(max(limit, 1), GIOI_HAN_TOI_DA)
        vi_tri = max(offset, 0)
        # Chuỗi rỗng/toàn khoảng trắng coi như không tìm kiếm, để ô tìm kiếm bị
        # xoá trắng không biến thành bộ lọc không khớp gì.
        tu_khoa = q.strip() if q and q.strip() else None

        conversations = await self._conversation_repo.list_for_scope(
            department_ids=pv.department_ids,
            include_awaiting=pv.include_awaiting,
            status=status,
            limit=gioi_han,
            offset=vi_tri,
            q=tu_khoa,
        )
        tong = await self._conversation_repo.count_for_scope(
            department_ids=pv.department_ids,
            include_awaiting=pv.include_awaiting,
            status=status,
            q=tu_khoa,
        )
        # Một truy vấn lấy preview cho cả trang, trước khi dựng từng dòng —
        # hỏi trong vòng lặp sẽ thành N+1 truy vấn.
        preview: dict[UUID, str] = {}
        if self._message_repo is not None and conversations:
            preview = await self._message_repo.last_texts_for_conversations(
                [c.id for c in conversations]
            )

        items = [await self._to_item(c, preview.get(c.id)) for c in conversations]
        return Page(items=items, total=tong, limit=gioi_han, offset=vi_tri)

    async def _to_item(self, conversation: Conversation, preview: str | None = None) -> InboxItem:
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
            last_message_preview=_rut_gon(preview),
        )
