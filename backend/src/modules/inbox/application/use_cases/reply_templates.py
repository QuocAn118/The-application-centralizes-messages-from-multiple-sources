"""Mẫu trả lời nhanh (BE-7).

- Xem: Admin mọi mẫu; người khác mẫu dùng chung + mẫu phòng mình.
- Tạo/sửa/xoá: Manager CHỈ mẫu của phòng mình (không tạo/sửa mẫu dùng chung);
  Admin mọi mẫu. Nhân viên chỉ đọc.
- Mẫu phòng khác với người gọi = không tồn tại (404), không lộ.
"""

from uuid import UUID

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.domain.entities.reply_template import ReplyTemplate
from src.modules.inbox.domain.repositories.reply_template_repository import (
    IReplyTemplateRepository,
)
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


def _khong_thay() -> NotFoundError:
    return NotFoundError("Không tìm thấy mẫu trả lời.", code="TEMPLATE_NOT_FOUND")


def _bao_dam_duoc_sua(actor: InboxActor, department_id: UUID | None) -> None:
    """Quyền GHI một mẫu thuộc ``department_id`` (``None`` = dùng chung)."""
    if actor.role is ActorRole.ADMIN:
        return
    if actor.role is not ActorRole.MANAGER:
        raise PermissionDeniedError(
            "Chỉ quản lý hoặc quản trị viên được sửa mẫu trả lời.",
            code="TEMPLATE_MANAGE_FORBIDDEN",
        )
    if department_id is None:
        raise PermissionDeniedError(
            "Chỉ quản trị viên được sửa mẫu dùng chung.", code="TEMPLATE_SHARED_ADMIN_ONLY"
        )
    if department_id != actor.department_id:
        raise PermissionDeniedError(
            "Bạn chỉ được sửa mẫu của phòng mình.", code="TEMPLATE_OUT_OF_SCOPE"
        )


class ReplyTemplates:
    def __init__(self, repo: IReplyTemplateRepository, clock: IClock) -> None:
        self._repo = repo
        self._clock = clock

    async def danh_sach(self, actor: InboxActor) -> list[ReplyTemplate]:
        return await self._repo.list_visible(
            tat_ca=actor.role is ActorRole.ADMIN, department_id=actor.department_id
        )

    async def tao(
        self, actor: InboxActor, department_id: UUID | None, title: str, body: str
    ) -> ReplyTemplate:
        _bao_dam_duoc_sua(actor, department_id)
        mau = ReplyTemplate.tao(department_id, title, body, self._clock.now())
        await self._repo.add(mau)
        return mau

    async def sua(
        self, actor: InboxActor, template_id: UUID, title: str | None, body: str | None
    ) -> ReplyTemplate:
        mau = await self._lay_thay_duoc(actor, template_id)
        _bao_dam_duoc_sua(actor, mau.department_id)
        mau.sua(title, body, self._clock.now())
        await self._repo.update(mau)
        return mau

    async def xoa(self, actor: InboxActor, template_id: UUID) -> None:
        mau = await self._lay_thay_duoc(actor, template_id)
        _bao_dam_duoc_sua(actor, mau.department_id)
        await self._repo.delete(template_id)

    async def _lay_thay_duoc(self, actor: InboxActor, template_id: UUID) -> ReplyTemplate:
        mau = await self._repo.get_by_id(template_id)
        if mau is None:
            raise _khong_thay()
        thay_duoc = (
            actor.role is ActorRole.ADMIN
            or mau.department_id is None
            or mau.department_id == actor.department_id
        )
        if not thay_duoc:
            raise _khong_thay()
        return mau
