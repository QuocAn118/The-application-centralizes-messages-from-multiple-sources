"""Entity phòng ban."""

from dataclasses import dataclass
from datetime import datetime

from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import BusinessRuleViolationError


class EmptyDepartmentNameError(BusinessRuleViolationError):
    """Tên phòng ban không được rỗng."""

    def __init__(self) -> None:
        super().__init__(
            "Tên phòng ban không được để trống.",
            code="EMPTY_DEPARTMENT_NAME",
        )


class DepartmentHasActiveMembersError(BusinessRuleViolationError):
    """Không thể vô hiệu hoá phòng ban còn nhân viên đang hoạt động."""

    def __init__(self, so_nhan_vien: int) -> None:
        super().__init__(
            f"Phòng ban còn {so_nhan_vien} nhân viên đang hoạt động. "
            "Hãy chuyển hoặc vô hiệu hoá họ trước.",
            code="DEPARTMENT_HAS_ACTIVE_MEMBERS",
        )


@dataclass(eq=False, kw_only=True)
class Department(AggregateRoot):
    """Phòng ban — đơn vị tổ chức và cũng là phạm vi phân quyền của Manager.

    Danh sách phẳng, không có phòng cha hay phòng con.
    """

    name: str
    description: str | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def _chuan_hoa_ten(name: str) -> str:
        ten = name.strip()
        if not ten:
            raise EmptyDepartmentNameError
        return ten

    @classmethod
    def create(cls, name: str, description: str | None, now: datetime) -> "Department":
        """Tạo phòng ban mới ở trạng thái hoạt động."""
        return cls(
            name=cls._chuan_hoa_ten(name),
            description=description,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    def rename(self, new_name: str, now: datetime) -> None:
        self.name = self._chuan_hoa_ten(new_name)
        self.updated_at = now

    def update_description(self, description: str | None, now: datetime) -> None:
        self.description = description
        self.updated_at = now

    def deactivate(self, active_member_count: int, now: datetime) -> None:
        """Vô hiệu hoá phòng ban.

        ``active_member_count`` do use case đếm và truyền vào — domain entity
        không truy cập repository.
        """
        if active_member_count > 0:
            raise DepartmentHasActiveMembersError(active_member_count)
        self.is_active = False
        self.updated_at = now
