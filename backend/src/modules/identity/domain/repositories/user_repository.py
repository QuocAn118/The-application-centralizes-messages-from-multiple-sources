"""Interface repository cho người dùng."""

from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.role import Role


class IUserRepository(Protocol):
    """Truy xuất và lưu trữ người dùng."""

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: Email) -> User | None: ...

    async def add(self, user: User) -> None: ...

    async def update(self, user: User) -> None: ...

    async def list_users(
        self,
        department_id: UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        """Danh sách người dùng đã lọc.

        ``search`` khớp không phân biệt hoa thường trên họ tên và email.
        """
        ...

    async def count_users(
        self,
        department_id: UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> int:
        """Đếm theo cùng bộ lọc với ``list_users`` — dùng cho phân trang."""
        ...

    async def count_active_in_department(self, department_id: UUID) -> int:
        """Số nhân viên đang hoạt động của một phòng ban.

        Dùng khi vô hiệu hoá phòng ban.
        """
        ...

    async def has_active_manager(
        self, department_id: UUID, exclude_user_id: UUID | None = None
    ) -> bool:
        """Phòng ban đã có quản lý đang hoạt động chưa.

        ``exclude_user_id`` để loại chính người đang được sửa ra khỏi phép
        kiểm tra, tránh trường hợp một Manager tự xung đột với chính mình.
        """
        ...

    async def count_active_admins(self) -> int:
        """Số quản trị viên đang hoạt động — dùng khi vô hiệu hoá Admin."""
        ...
