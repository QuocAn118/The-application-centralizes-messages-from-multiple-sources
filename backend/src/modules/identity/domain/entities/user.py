"""Entity người dùng."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import BusinessRuleViolationError


class DepartmentRequiredError(BusinessRuleViolationError):
    """Staff và Manager bắt buộc thuộc một phòng ban."""

    def __init__(self, role: Role) -> None:
        super().__init__(
            f"Vai trò {role.value} bắt buộc phải thuộc một phòng ban.",
            code="DEPARTMENT_REQUIRED",
        )


class AdminCannotHaveDepartmentError(BusinessRuleViolationError):
    """Admin quản trị toàn hệ thống nên không gắn với phòng ban."""

    def __init__(self) -> None:
        super().__init__(
            "Quản trị viên không thuộc phòng ban nào.",
            code="ADMIN_CANNOT_HAVE_DEPARTMENT",
        )


class DepartmentAlreadyHasManagerError(BusinessRuleViolationError):
    """Mỗi phòng ban chỉ có tối đa một quản lý đang hoạt động."""

    def __init__(self) -> None:
        super().__init__(
            "Phòng ban này đã có một quản lý đang hoạt động.",
            code="DEPARTMENT_ALREADY_HAS_MANAGER",
        )


class LastAdminCannotBeDeactivatedError(BusinessRuleViolationError):
    """Hệ thống phải luôn còn ít nhất một quản trị viên hoạt động."""

    def __init__(self) -> None:
        super().__init__(
            "Không thể vô hiệu hoá quản trị viên cuối cùng của hệ thống.",
            code="LAST_ADMIN_CANNOT_BE_DEACTIVATED",
        )


class InactiveDepartmentError(BusinessRuleViolationError):
    """Không thể kích hoạt lại nhân viên thuộc phòng ban đã bị vô hiệu hoá."""

    def __init__(self) -> None:
        super().__init__(
            "Phòng ban của nhân viên này đã bị vô hiệu hoá. "
            "Hãy chuyển họ sang phòng ban khác trước khi kích hoạt lại.",
            code="INACTIVE_DEPARTMENT",
        )


class EmptyFullNameError(BusinessRuleViolationError):
    """Họ tên không được rỗng."""

    def __init__(self) -> None:
        super().__init__("Họ tên không được để trống.", code="EMPTY_FULL_NAME")


class CannotChangeToAdminError(BusinessRuleViolationError):
    """Chỉ cho phép chuyển đổi giữa Staff và Manager."""

    def __init__(self) -> None:
        super().__init__(
            "Chỉ có thể chuyển đổi giữa Nhân viên và Quản lý. "
            "Tài khoản quản trị viên phải được tạo riêng.",
            code="CANNOT_CHANGE_TO_ADMIN",
        )


@dataclass(eq=False, kw_only=True)
class User(AggregateRoot):
    """Người dùng hệ thống — Staff, Manager hoặc Admin dùng chung một entity.

    Mọi kiểm tra cần dữ liệu nằm ngoài entity (phòng ban đã có quản lý chưa,
    đây có phải admin cuối cùng không) được nhận qua tham số. Use case tra cứu
    rồi truyền vào, nhờ đó domain không phụ thuộc repository.
    """

    email: Email
    password_hash: PasswordHash
    full_name: str
    role: Role
    created_at: datetime
    updated_at: datetime
    phone: str | None = None
    department_id: UUID | None = None
    is_active: bool = True
    must_change_password: bool = True
    last_login_at: datetime | None = None

    @staticmethod
    def _kiem_tra_phong_ban(role: Role, department_id: UUID | None) -> None:
        if role.requires_department() and department_id is None:
            raise DepartmentRequiredError(role)
        if not role.requires_department() and department_id is not None:
            raise AdminCannotHaveDepartmentError

    @staticmethod
    def _chuan_hoa_ho_ten(full_name: str) -> str:
        ten = full_name.strip()
        if not ten:
            raise EmptyFullNameError
        return ten

    @classmethod
    def create(
        cls,
        email: Email,
        password_hash: PasswordHash,
        full_name: str,
        role: Role,
        department_id: UUID | None,
        now: datetime,
        phone: str | None = None,
        must_change_password: bool = True,
    ) -> "User":
        """Tạo người dùng mới.

        Mặc định ``must_change_password=True`` vì tài khoản do Admin cấp kèm
        mật khẩu tạm.
        """
        cls._kiem_tra_phong_ban(role, department_id)
        return cls(
            email=email,
            password_hash=password_hash,
            full_name=cls._chuan_hoa_ho_ten(full_name),
            phone=phone,
            role=role,
            department_id=department_id,
            is_active=True,
            must_change_password=must_change_password,
            last_login_at=None,
            created_at=now,
            updated_at=now,
        )

    def change_role(
        self,
        new_role: Role,
        department_id: UUID | None,
        department_has_active_manager: bool,
        now: datetime,
    ) -> None:
        """Chuyển đổi giữa Staff và Manager.

        ``department_has_active_manager`` phải được tính cho ``department_id``
        đích và không tính chính người dùng này.
        """
        if new_role is Role.ADMIN:
            raise CannotChangeToAdminError
        if self.role is Role.ADMIN:
            raise CannotChangeToAdminError

        self._kiem_tra_phong_ban(new_role, department_id)
        if new_role is Role.MANAGER and department_has_active_manager:
            raise DepartmentAlreadyHasManagerError

        self.role = new_role
        self.department_id = department_id
        self.updated_at = now

    def assign_to_department(
        self,
        department_id: UUID | None,
        department_has_active_manager: bool,
        now: datetime,
    ) -> None:
        """Chuyển người dùng sang phòng ban khác, giữ nguyên vai trò."""
        self._kiem_tra_phong_ban(self.role, department_id)
        if self.role is Role.MANAGER and department_has_active_manager:
            raise DepartmentAlreadyHasManagerError

        self.department_id = department_id
        self.updated_at = now

    def deactivate(self, is_last_active_admin: bool, now: datetime) -> None:
        """Vô hiệu hoá tài khoản.

        Việc thu hồi refresh token do use case đảm nhiệm, không thuộc entity.
        """
        if self.role is Role.ADMIN and is_last_active_admin:
            raise LastAdminCannotBeDeactivatedError
        self.is_active = False
        self.updated_at = now

    def reactivate(
        self,
        department_is_active: bool,
        department_has_active_manager: bool,
        now: datetime,
    ) -> None:
        """Kích hoạt lại tài khoản đã bị vô hiệu hoá."""
        if self.role.requires_department():
            if not department_is_active:
                raise InactiveDepartmentError
            if self.role is Role.MANAGER and department_has_active_manager:
                raise DepartmentAlreadyHasManagerError

        self.is_active = True
        self.updated_at = now

    def set_password(self, password_hash: PasswordHash, must_change: bool, now: datetime) -> None:
        """Đặt mật khẩu mới.

        ``must_change=True`` khi Admin cấp mật khẩu tạm; ``False`` khi chính
        người dùng tự đổi.
        """
        self.password_hash = password_hash
        self.must_change_password = must_change
        self.updated_at = now

    def record_login(self, now: datetime) -> None:
        self.last_login_at = now

    def update_profile(self, full_name: str | None, phone: str | None, now: datetime) -> None:
        """Cập nhật thông tin hồ sơ. Tham số ``None`` nghĩa là giữ nguyên."""
        if full_name is not None:
            self.full_name = self._chuan_hoa_ho_ten(full_name)
        if phone is not None:
            self.phone = phone
        self.updated_at = now

    def can_manage(self, other: "User") -> bool:
        """Người dùng này có quyền quản lý ``other`` không.

        Admin quản lý được mọi người. Manager chỉ quản lý được Staff cùng
        phòng ban. Staff không quản lý được ai.
        """
        if self.role is Role.ADMIN:
            return True
        if self.role is Role.MANAGER:
            return other.role is Role.STAFF and other.department_id == self.department_id
        return False
