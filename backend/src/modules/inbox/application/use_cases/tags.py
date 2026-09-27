"""Nhãn khách dùng chung (BE-6).

- Xem danh sách nhãn đang dùng: mọi vai. Kèm nhãn đã ngừng: chỉ Manager/Admin.
- Tạo / sửa / ngừng dùng: Manager/Admin (nhãn chung toàn công ty, không theo phòng).
- Gắn/gỡ cho khách: ai "đụng được" khách (như ghi chú). Chỉ gắn MỚI được nhãn đang
  dùng; nhãn đã ngừng mà khách đang có thì giữ được (gửi lại nguyên danh sách).
"""

from uuid import UUID

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.customer_notes import bao_dam_dung_toi_khach
from src.modules.inbox.domain.entities.tag import Tag
from src.modules.inbox.domain.repositories.conversation_repository import (
    IConversationRepository,
)
from src.modules.inbox.domain.repositories.tag_repository import ITagRepository
from src.shared.application.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.shared.application.ports import IClock


def _bao_dam_quan_ly(actor: InboxActor) -> None:
    if actor.role not in (ActorRole.ADMIN, ActorRole.MANAGER):
        raise PermissionDeniedError(
            "Chỉ quản lý hoặc quản trị viên được quản lý nhãn.", code="TAG_MANAGE_FORBIDDEN"
        )


class Tags:
    def __init__(
        self, tag_repo: ITagRepository, conversation_repo: IConversationRepository, clock: IClock
    ) -> None:
        self._tags = tag_repo
        self._conversations = conversation_repo
        self._clock = clock

    async def danh_sach(self, actor: InboxActor, include_inactive: bool) -> list[Tag]:
        # Staff xin cả nhãn đã ngừng thì lặng lẽ chỉ trả nhãn đang dùng.
        return await self._tags.list_all(include_inactive and actor.role is not ActorRole.STAFF)

    async def tao(self, actor: InboxActor, name: str, color: str) -> Tag:
        _bao_dam_quan_ly(actor)
        nhan = Tag.tao(name, color, self._clock.now())
        await self._bao_dam_ten_chua_dung(nhan.name, bo_qua=None)
        await self._tags.add(nhan)
        return nhan

    async def sua(
        self,
        actor: InboxActor,
        tag_id: UUID,
        name: str | None,
        color: str | None,
        is_active: bool | None,
    ) -> Tag:
        _bao_dam_quan_ly(actor)
        nhan = await self._tags.get_by_id(tag_id)
        if nhan is None:
            raise NotFoundError("Không tìm thấy nhãn.", code="TAG_NOT_FOUND")
        nhan.sua(name, color, is_active)
        if name is not None:
            await self._bao_dam_ten_chua_dung(nhan.name, bo_qua=nhan.id)
        await self._tags.update(nhan)
        return nhan

    async def cua_khach(self, actor: InboxActor, customer_id: UUID) -> list[Tag]:
        await bao_dam_dung_toi_khach(actor, customer_id, self._conversations)
        return await self._tags.list_for_customer(customer_id)

    async def gan_cho_khach(
        self, actor: InboxActor, customer_id: UUID, tag_ids: list[UUID]
    ) -> list[Tag]:
        await bao_dam_dung_toi_khach(actor, customer_id, self._conversations)
        muon = list(dict.fromkeys(tag_ids))
        co_that = {t.id: t for t in await self._tags.get_many(muon)}
        dang_co = {t.id for t in await self._tags.list_for_customer(customer_id)}
        for tid in muon:
            nhan = co_that.get(tid)
            if nhan is None or (not nhan.is_active and tid not in dang_co):
                raise NotFoundError("Không tìm thấy nhãn đang dùng.", code="TAG_NOT_FOUND")
        await self._tags.set_for_customer(customer_id, muon)
        return sorted(co_that.values(), key=lambda t: t.name.lower())

    async def _bao_dam_ten_chua_dung(self, name: str, bo_qua: UUID | None) -> None:
        trung = await self._tags.find_by_name(name)
        if trung is not None and trung.id != bo_qua:
            raise ConflictError(f'Đã có nhãn "{trung.name}".', code="TAG_NAME_TAKEN")
