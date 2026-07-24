"""Use case liệt kê phòng ban."""

from src.modules.identity.application.dto.user_dto import Page
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)

GIOI_HAN_TOI_DA = 100


class ListDepartments:
    """Liệt kê phòng ban.

    Mọi người dùng đã đăng nhập đều xem được: giao diện cần tên phòng ban để
    hiển thị, và danh sách này không chứa thông tin nhạy cảm.
    """

    def __init__(self, department_repo: IDepartmentRepository) -> None:
        self._department_repo = department_repo

    async def execute(
        self,
        requester: User,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[Department]:
        gioi_han = min(max(limit, 1), GIOI_HAN_TOI_DA)
        vi_tri = max(offset, 0)

        items = await self._department_repo.list_departments(
            is_active=is_active, limit=gioi_han, offset=vi_tri
        )
        tong = await self._department_repo.count_departments(is_active=is_active)
        return Page(items=items, total=tong, limit=gioi_han, offset=vi_tri)
