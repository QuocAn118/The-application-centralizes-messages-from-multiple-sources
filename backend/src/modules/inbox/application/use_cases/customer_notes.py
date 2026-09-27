"""Ghi chú nội bộ về khách theo phòng (BE-5, GĐ1 §10.4).

Luật:
- **Đụng được tới khách** = có ít nhất một hội thoại của khách nằm trong phạm vi
  xem của người gọi (cùng phạm vi với ``GET /inbox``). Không → 404 như khách không
  tồn tại (không lộ thông tin).
- Xem: Admin thấy mọi ghi chú; người khác CHỈ ghi chú có ``department_id`` = phòng
  mình. Người không phải Admin mà không có phòng thì không thấy/không viết gì — nếu
  không, ``department_id = None`` của họ sẽ khớp nhầm ghi chú của Admin.
- Xoá: người viết (khi vẫn cùng phòng với ghi chú) hoặc Admin.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.list_inbox import pham_vi_cua
from src.modules.inbox.domain.entities.customer_note import CustomerNote
from src.modules.inbox.domain.ports import IWorkforceDirectory
from src.modules.inbox.domain.repositories.conversation_repository import (
    IConversationRepository,
)
from src.modules.inbox.domain.repositories.customer_note_repository import (
    ICustomerNoteRepository,
)
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


@dataclass(frozen=True)
class NoteView:
    id: UUID
    customer_id: UUID
    department_id: UUID | None
    department_name: str | None
    author_id: UUID
    author_name: str | None
    body: str
    created_at: datetime


def _khong_thay_khach() -> NotFoundError:
    return NotFoundError("Không tìm thấy khách.", code="CUSTOMER_NOT_FOUND")


async def bao_dam_dung_toi_khach(
    actor: InboxActor, customer_id: UUID, conversation_repo: IConversationRepository
) -> None:
    """Dùng chung cho ghi chú (BE-5) và nhãn (BE-6)."""
    pv = pham_vi_cua(actor)
    so = await conversation_repo.count_for_scope(
        department_ids=pv.department_ids,
        include_awaiting=pv.include_awaiting,
        customer_id=customer_id,
    )
    if so == 0:
        raise _khong_thay_khach()


def _khong_co_phong(actor: InboxActor) -> bool:
    return actor.role is not ActorRole.ADMIN and actor.department_id is None


class CustomerNotes:
    def __init__(
        self,
        note_repo: ICustomerNoteRepository,
        conversation_repo: IConversationRepository,
        directory: IWorkforceDirectory,
        clock: IClock,
    ) -> None:
        self._notes = note_repo
        self._conversations = conversation_repo
        self._directory = directory
        self._clock = clock

    async def xem(self, actor: InboxActor, customer_id: UUID) -> list[NoteView]:
        await bao_dam_dung_toi_khach(actor, customer_id, self._conversations)
        if _khong_co_phong(actor):
            return []
        ghi_chu = await self._notes.list_for_customer(
            customer_id,
            tat_ca_phong=actor.role is ActorRole.ADMIN,
            department_id=actor.department_id,
        )
        return await self._views(ghi_chu)

    async def viet(self, actor: InboxActor, customer_id: UUID, body: str) -> NoteView:
        await bao_dam_dung_toi_khach(actor, customer_id, self._conversations)
        if _khong_co_phong(actor):
            raise PermissionDeniedError(
                "Tài khoản chưa thuộc phòng nào nên không viết được ghi chú.",
                code="NOTE_NO_DEPARTMENT",
            )
        ghi_chu = CustomerNote.viet(
            customer_id, actor.department_id, actor.user_id, body, self._clock.now()
        )
        await self._notes.add(ghi_chu)
        (view,) = await self._views([ghi_chu])
        return view

    async def xoa(self, actor: InboxActor, note_id: UUID) -> None:
        ghi_chu = await self._notes.get_by_id(note_id)
        la_admin = actor.role is ActorRole.ADMIN
        # Ghi chú phòng khác = như không tồn tại với người gọi.
        if ghi_chu is None or (
            not la_admin
            and (_khong_co_phong(actor) or ghi_chu.department_id != actor.department_id)
        ):
            raise NotFoundError("Không tìm thấy ghi chú.", code="NOTE_NOT_FOUND")
        if not la_admin and ghi_chu.author_id != actor.user_id:
            raise PermissionDeniedError(
                "Chỉ người viết hoặc quản trị viên được xoá ghi chú.",
                code="NOTE_DELETE_FORBIDDEN",
            )
        await self._notes.delete(note_id)

    async def _views(self, ghi_chu: list[CustomerNote]) -> list[NoteView]:
        ten = await self._directory.get_names(list({g.author_id for g in ghi_chu}))
        phong = await self._directory.get_department_names(
            list({g.department_id for g in ghi_chu if g.department_id is not None})
        )
        return [
            NoteView(
                id=g.id,
                customer_id=g.customer_id,
                department_id=g.department_id,
                department_name=phong.get(g.department_id) if g.department_id else None,
                author_id=g.author_id,
                author_name=ten.get(g.author_id),
                body=g.body,
                created_at=g.created_at,
            )
            for g in ghi_chu
        ]
