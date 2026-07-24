"""Use case liệt kê người dùng."""

from uuid import UUID

from src.modules.identity.application.dto.user_dto import Page
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import PermissionDeniedError

GIOI_HAN_TOI_DA = 100


class ListUsers:
    """Liệt kê người dùng theo phạm vi quyền của người gọi.

    Quản lý chỉ thấy được phòng ban của mình, kể cả khi họ truyền
    ``department_id`` của phòng khác — bộ lọc bị ghi đè chứ không báo lỗi, để
    không tiết lộ phòng ban nào tồn tại.
    """

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def execute(
        self,
        requester: User,
        department_id: UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[User]:
        if requester.role is Role.STAFF:
            raise PermissionDeniedError(
                "Bạn không có quyền xem danh sách người dùng.",
                code="INSUFFICIENT_ROLE",
            )

        pham_vi = department_id
        if requester.role is Role.MANAGER:
            pham_vi = requester.department_id

        gioi_han = min(max(limit, 1), GIOI_HAN_TOI_DA)
        vi_tri = max(offset, 0)

        items = await self._user_repo.list_users(
            department_id=pham_vi,
            role=role,
            is_active=is_active,
            search=search,
            limit=gioi_han,
            offset=vi_tri,
        )
        tong = await self._user_repo.count_users(
            department_id=pham_vi, role=role, is_active=is_active, search=search
        )
        return Page(items=items, total=tong, limit=gioi_han, offset=vi_tri)
