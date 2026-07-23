# OmniChat Foundation — Phần 2: Domain Identity (Task 4–8)

> Tiếp nối [phần 1](2026-07-21-omnichat-foundation.md). Global Constraints ở phần 1 áp dụng cho mọi task tại đây.

Giai đoạn này viết toàn bộ business rule dưới dạng Python thuần. Không có SQLAlchemy, không có FastAPI, không có Pydantic — mọi test chạy trong mili giây và không cần cơ sở dữ liệu.

---

## Task 4: Value object `Email`, `Role`, `PasswordHash`

**Files:**
- Create: `backend/src/modules/__init__.py`
- Create: `backend/src/modules/identity/__init__.py`
- Create: `backend/src/modules/identity/domain/__init__.py`
- Create: `backend/src/modules/identity/domain/value_objects/__init__.py`
- Create: `backend/src/modules/identity/domain/value_objects/email.py`
- Create: `backend/src/modules/identity/domain/value_objects/role.py`
- Create: `backend/src/modules/identity/domain/value_objects/password_hash.py`
- Test: `backend/tests/unit/identity/__init__.py`
- Test: `backend/tests/unit/identity/test_value_objects.py`

**Interfaces:**
- Consumes: `ValueObject`, `DomainError` từ Task 2.
- Produces:
  - `Email(value: str)` — frozen dataclass. Chuẩn hoá về chữ thường và cắt khoảng trắng khi khởi tạo. Ném `InvalidEmailError` nếu sai định dạng. Thuộc tính `.value`.
  - `Role` — `StrEnum` với ba thành viên `STAFF`, `MANAGER`, `ADMIN`. Phương thức `.requires_department() -> bool` trả về `True` cho `STAFF` và `MANAGER`.
  - `PasswordHash(value: str)` — frozen dataclass bọc chuỗi hash đã băm. Ném `InvalidPasswordHashError` nếu chuỗi rỗng. Thuộc tính `.value`.
  - `InvalidEmailError`, `InvalidPasswordHashError` — kế thừa `DomainError`.

- [ ] **Step 1: Viết test thất bại**

File `backend/tests/unit/identity/test_value_objects.py`:

```python
from dataclasses import FrozenInstanceError

import pytest

from src.modules.identity.domain.value_objects.email import (
    DO_DAI_EMAIL_TOI_DA,
    Email,
    EmailTooLongError,
    InvalidEmailError,
)
from src.modules.identity.domain.value_objects.password_hash import (
    InvalidPasswordHashError,
    PasswordHash,
)
from src.modules.identity.domain.value_objects.role import Role


class TestEmail:
    def test_chap_nhan_email_hop_le(self) -> None:
        assert Email("nhanvien@congty.vn").value == "nhanvien@congty.vn"

    def test_chuyen_ve_chu_thuong(self) -> None:
        assert Email("NhanVien@CongTy.VN").value == "nhanvien@congty.vn"

    def test_cat_khoang_trang_thua(self) -> None:
        assert Email("  a@b.vn  ").value == "a@b.vn"

    @pytest.mark.parametrize(
        "gia_tri_sai",
        ["", "   ", "khong-co-a-cong", "@thieu-phan-dau.vn", "thieu-duoi@", "a@b", "a b@c.vn"],
    )
    def test_tu_choi_email_sai_dinh_dang(self, gia_tri_sai: str) -> None:
        with pytest.raises(InvalidEmailError):
            Email(gia_tri_sai)

    def test_hai_email_cung_gia_tri_thi_bang_nhau(self) -> None:
        assert Email("a@b.vn") == Email("A@B.VN")

    def test_chap_nhan_email_dung_bang_gioi_han(self) -> None:
        phan_dau = "a" * (DO_DAI_EMAIL_TOI_DA - len("@congty.vn"))
        dung_gioi_han = f"{phan_dau}@congty.vn"

        assert len(Email(dung_gioi_han).value) == DO_DAI_EMAIL_TOI_DA

    def test_tu_choi_email_vuot_gioi_han(self) -> None:
        """Cột ``users.email`` là VARCHAR(320) — domain phải chặn trước khi
        cơ sở dữ liệu ném DataError khó truy nguyên."""
        qua_dai = "a" * (DO_DAI_EMAIL_TOI_DA - len("@congty.vn") + 1) + "@congty.vn"

        with pytest.raises(EmailTooLongError):
            Email(qua_dai)

    def test_khong_the_thay_doi_sau_khi_tao(self) -> None:
        email = Email("a@b.vn")
        with pytest.raises(FrozenInstanceError):
            email.value = "c@d.vn"  # type: ignore[misc]


class TestRole:
    def test_co_dung_ba_vai_tro(self) -> None:
        assert {r.value for r in Role} == {"STAFF", "MANAGER", "ADMIN"}

    @pytest.mark.parametrize("vai_tro", [Role.STAFF, Role.MANAGER])
    def test_staff_va_manager_bat_buoc_thuoc_phong_ban(self, vai_tro: Role) -> None:
        assert vai_tro.requires_department() is True

    def test_admin_khong_thuoc_phong_ban_nao(self) -> None:
        assert Role.ADMIN.requires_department() is False

    def test_so_sanh_duoc_voi_chuoi(self) -> None:
        assert Role.STAFF == "STAFF"


class TestPasswordHash:
    def test_giu_nguyen_chuoi_hash(self) -> None:
        chuoi = "$2b$12$abcdefghijklmnopqrstuv"
        assert PasswordHash(chuoi).value == chuoi

    @pytest.mark.parametrize("gia_tri_sai", ["", "   "])
    def test_tu_choi_chuoi_rong(self, gia_tri_sai: str) -> None:
        with pytest.raises(InvalidPasswordHashError):
            PasswordHash(gia_tri_sai)

    def test_khong_lo_hash_khi_in_ra(self) -> None:
        """Hash không được xuất hiện trong log hay thông báo lỗi."""
        hash_that = "$2b$12$chuoi_hash_bi_mat"
        assert hash_that not in repr(PasswordHash(hash_that))
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/unit/identity/test_value_objects.py -v
```

Expected: FAIL với `ModuleNotFoundError: No module named 'src.modules'`.

- [ ] **Step 3: Viết `email.py`**

```python
"""Value object địa chỉ email."""

import re
from dataclasses import dataclass

from src.shared.domain.exceptions import DomainError

_DINH_DANG_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Giới hạn của RFC 5321 và cũng là độ rộng cột ``users.email`` (VARCHAR 320).
# Domain phải từ chối thứ mà cơ sở dữ liệu không lưu nổi, nếu không lỗi sẽ nổ ở
# tầng lưu trữ dưới dạng DataError khó truy nguyên.
DO_DAI_EMAIL_TOI_DA = 320


class InvalidEmailError(DomainError):
    """Địa chỉ email không đúng định dạng."""

    def __init__(self, gia_tri: str) -> None:
        super().__init__(
            f"Địa chỉ email không hợp lệ: {gia_tri!r}",
            code="INVALID_EMAIL",
        )


class EmailTooLongError(DomainError):
    """Địa chỉ email vượt quá độ dài tối đa."""

    def __init__(self, do_dai: int) -> None:
        super().__init__(
            f"Địa chỉ email dài {do_dai} ký tự, vượt quá giới hạn "
            f"{DO_DAI_EMAIL_TOI_DA} ký tự.",
            code="EMAIL_TOO_LONG",
        )


@dataclass(frozen=True)
class Email:
    """Địa chỉ email đã được chuẩn hoá.

    Chuẩn hoá về chữ thường ngay khi khởi tạo, nên hai địa chỉ chỉ khác nhau
    ở kiểu chữ sẽ bằng nhau. Nhờ đó ràng buộc duy nhất ở cơ sở dữ liệu
    (index trên ``lower(email)``) khớp với hành vi của tầng domain.
    """

    value: str

    def __post_init__(self) -> None:
        chuan_hoa = self.value.strip().lower()
        if not _DINH_DANG_EMAIL.match(chuan_hoa):
            raise InvalidEmailError(self.value)
        if len(chuan_hoa) > DO_DAI_EMAIL_TOI_DA:
            raise EmailTooLongError(len(chuan_hoa))
        object.__setattr__(self, "value", chuan_hoa)

    def __str__(self) -> str:
        return self.value
```

- [ ] **Step 4: Viết `role.py`**

```python
"""Vai trò người dùng trong hệ thống."""

from enum import StrEnum


class Role(StrEnum):
    """Ba vai trò của OmniChat.

    Kế thừa ``StrEnum`` để so sánh trực tiếp với chuỗi, thuận tiện khi đọc
    giá trị từ cơ sở dữ liệu và khi ghi ra JSON.
    """

    STAFF = "STAFF"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"

    def requires_department(self) -> bool:
        """Vai trò này có bắt buộc thuộc một phòng ban không.

        Admin quản trị toàn hệ thống nên không gắn với phòng ban nào; Staff và
        Manager luôn thuộc đúng một phòng ban.
        """
        return self is not Role.ADMIN
```

- [ ] **Step 5: Viết `password_hash.py`**

```python
"""Value object chuỗi mật khẩu đã băm."""

from dataclasses import dataclass

from src.shared.domain.exceptions import DomainError


class InvalidPasswordHashError(DomainError):
    """Chuỗi hash mật khẩu rỗng hoặc không hợp lệ."""

    def __init__(self) -> None:
        super().__init__(
            "Chuỗi hash mật khẩu không được rỗng.",
            code="INVALID_PASSWORD_HASH",
        )


@dataclass(frozen=True)
class PasswordHash:
    """Bọc chuỗi mật khẩu đã băm.

    Tồn tại để kiểu dữ liệu tự nói lên rằng đây là hash chứ không phải mật khẩu
    thô, tránh nhầm lẫn khi truyền tham số. ``__repr__`` được ghi đè để hash
    không lọt vào log hay thông báo lỗi.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise InvalidPasswordHashError

    def __repr__(self) -> str:
        return "PasswordHash(<đã ẩn>)"

    def __str__(self) -> str:
        return "<đã ẩn>"
```

- [ ] **Step 6: Tạo các file `__init__.py`**

```bash
cd backend
mkdir -p src/modules/identity/domain/value_objects \
         src/modules/identity/application \
         src/modules/identity/infrastructure \
         src/modules/identity/presentation \
         tests/unit/identity
touch src/modules/__init__.py src/modules/identity/__init__.py \
      src/modules/identity/domain/__init__.py \
      src/modules/identity/domain/value_objects/__init__.py \
      src/modules/identity/application/__init__.py \
      src/modules/identity/infrastructure/__init__.py \
      src/modules/identity/presentation/__init__.py \
      tests/unit/identity/__init__.py
```

Ba thư mục `application/`, `infrastructure/` và `presentation/` được tạo rỗng ngay từ đây dù mãi Task 13, 9 và 16 mới có nội dung. Lý do: contract của `import-linter` tham chiếu cả bốn layer, và công cụ này báo lỗi cấu hình nếu một module trong contract chưa tồn tại. Tạo sẵn khiến kiểm tra kiến trúc chạy được từ Task 4 thay vì phải đợi tới Task 16 — vi phạm dependency rule bị bắt ngay lúc phát sinh.

- [ ] **Step 7: Chạy test để xác nhận thành công**

```bash
uv run pytest tests/unit/identity/test_value_objects.py -v
```

Expected: `21 passed` (các test dùng `parametrize` nở ra nhiều trường hợp).

- [ ] **Step 8: Kiểm tra chất lượng mã**

```bash
uv run mypy src
uv run ruff check .
uv run lint-imports
```

Expected: mypy và ruff xanh. `lint-imports` in `Contracts: 3 kept, 0 broken.` — đây là lần đầu tiên nó chạy được, nhờ ba thư mục layer rỗng tạo ở Step 6.

- [ ] **Step 9: Commit**

```bash
git add backend/src/modules backend/tests/unit/identity
git commit -m "feat: add identity value objects for email, role, and password hash"
```

---

## Task 5: Entity `Department`

**Files:**
- Create: `backend/src/modules/identity/domain/entities/__init__.py`
- Create: `backend/src/modules/identity/domain/entities/department.py`
- Test: `backend/tests/unit/identity/test_department.py`

**Interfaces:**
- Consumes: `AggregateRoot`, `BusinessRuleViolationError` từ Task 2.
- Produces:
  - `Department` — `AggregateRoot`. Trường: `id: UUID`, `name: str`, `description: str | None`, `is_active: bool`, `created_at: datetime`, `updated_at: datetime`.
  - `Department.create(name: str, description: str | None, now: datetime) -> Department` — factory, chuẩn hoá tên, ném `EmptyDepartmentNameError` nếu tên rỗng.
  - `Department.rename(new_name: str, now: datetime) -> None`.
  - `Department.update_description(description: str | None, now: datetime) -> None`.
  - `Department.deactivate(active_member_count: int, now: datetime) -> None` — ném `DepartmentHasActiveMembersError` nếu `active_member_count > 0`.
  - `EmptyDepartmentNameError`, `DepartmentHasActiveMembersError` — kế thừa `BusinessRuleViolationError`.

**Ghi chú thiết kế:** `deactivate` nhận `active_member_count` làm tham số thay vì tự truy vấn. Domain entity không được biết tới repository; use case đếm trước rồi truyền vào. Nhờ vậy quy tắc vẫn nằm trong domain và test được mà không cần cơ sở dữ liệu.

- [ ] **Step 1: Viết test thất bại**

File `backend/tests/unit/identity/test_department.py`:

```python
from datetime import UTC, datetime

import pytest

from src.modules.identity.domain.entities.department import (
    Department,
    DepartmentHasActiveMembersError,
    EmptyDepartmentNameError,
)

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
SAU_DO = datetime(2026, 7, 21, 11, 0, tzinfo=UTC)


def _tao_phong_ban(ten: str = "Tư vấn sản phẩm A") -> Department:
    return Department.create(name=ten, description=None, now=BAY_GIO)


class TestTaoPhongBan:
    def test_phong_ban_moi_o_trang_thai_hoat_dong(self) -> None:
        phong = _tao_phong_ban()

        assert phong.is_active is True
        assert phong.name == "Tư vấn sản phẩm A"
        assert phong.created_at == BAY_GIO
        assert phong.updated_at == BAY_GIO

    def test_cat_khoang_trang_thua_trong_ten(self) -> None:
        assert _tao_phong_ban("  Kinh doanh  ").name == "Kinh doanh"

    @pytest.mark.parametrize("ten_sai", ["", "   ", "\t\n"])
    def test_tu_choi_ten_rong(self, ten_sai: str) -> None:
        with pytest.raises(EmptyDepartmentNameError):
            _tao_phong_ban(ten_sai)


class TestDoiTenPhongBan:
    def test_doi_ten_cap_nhat_ca_moc_thoi_gian(self) -> None:
        phong = _tao_phong_ban()

        phong.rename("Chăm sóc khách hàng", now=SAU_DO)

        assert phong.name == "Chăm sóc khách hàng"
        assert phong.updated_at == SAU_DO

    def test_tu_choi_doi_sang_ten_rong(self) -> None:
        phong = _tao_phong_ban()

        with pytest.raises(EmptyDepartmentNameError):
            phong.rename("   ", now=SAU_DO)


class TestCapNhatMoTaPhongBan:
    def test_cap_nhat_mo_ta_va_moc_thoi_gian(self) -> None:
        phong = _tao_phong_ban()

        phong.update_description("Phòng phụ trách sản phẩm A", now=SAU_DO)

        assert phong.description == "Phòng phụ trách sản phẩm A"
        assert phong.updated_at == SAU_DO

    def test_xoa_mo_ta_bang_none(self) -> None:
        phong = Department.create(name="Kinh doanh", description="Cũ", now=BAY_GIO)

        phong.update_description(None, now=SAU_DO)

        assert phong.description is None


class TestVoHieuHoaPhongBan:
    def test_vo_hieu_hoa_duoc_khi_khong_con_nhan_vien(self) -> None:
        phong = _tao_phong_ban()

        phong.deactivate(active_member_count=0, now=SAU_DO)

        assert phong.is_active is False
        assert phong.updated_at == SAU_DO

    def test_tu_choi_khi_con_nhan_vien_dang_hoat_dong(self) -> None:
        phong = _tao_phong_ban()

        with pytest.raises(DepartmentHasActiveMembersError):
            phong.deactivate(active_member_count=3, now=SAU_DO)

        assert phong.is_active is True

    def test_vo_hieu_hoa_lai_lan_nua_khong_gay_loi(self) -> None:
        phong = _tao_phong_ban()
        phong.deactivate(active_member_count=0, now=SAU_DO)

        phong.deactivate(active_member_count=0, now=SAU_DO)

        assert phong.is_active is False
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/unit/identity/test_department.py -v
```

Expected: FAIL với `ModuleNotFoundError: No module named 'src.modules.identity.domain.entities'`.

- [ ] **Step 3: Viết `department.py`**

```python
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
```

- [ ] **Step 4: Tạo `__init__.py`**

```bash
cd backend
mkdir -p src/modules/identity/domain/entities
touch src/modules/identity/domain/entities/__init__.py
```

- [ ] **Step 5: Chạy test để xác nhận thành công**

```bash
uv run pytest tests/unit/identity/test_department.py -v
```

Expected: `9 passed`.

- [ ] **Step 6: Kiểm tra chất lượng mã**

```bash
uv run mypy src
uv run ruff check .
```

Expected: xanh.

- [ ] **Step 7: Commit**

```bash
git add backend/src/modules/identity/domain/entities backend/tests/unit/identity/test_department.py
git commit -m "feat: add department entity with deactivation rules"
```

---

## Task 6: Entity `User`

**Files:**
- Create: `backend/src/modules/identity/domain/entities/user.py`
- Test: `backend/tests/unit/identity/test_user.py`

**Interfaces:**
- Consumes: `AggregateRoot`, `BusinessRuleViolationError`, `Email`, `Role`, `PasswordHash`.
- Produces:
  - `User` — `AggregateRoot`. Trường: `id: UUID`, `email: Email`, `password_hash: PasswordHash`, `full_name: str`, `phone: str | None`, `role: Role`, `department_id: UUID | None`, `is_active: bool`, `must_change_password: bool`, `last_login_at: datetime | None`, `created_at: datetime`, `updated_at: datetime`.
  - `User.create(email, password_hash, full_name, role, department_id, now, phone=None, must_change_password=True) -> User`.
  - `User.change_role(new_role: Role, department_id: UUID | None, department_has_active_manager: bool, now: datetime) -> None`.
  - `User.assign_to_department(department_id: UUID | None, department_has_active_manager: bool, now: datetime) -> None`.
  - `User.deactivate(is_last_active_admin: bool, now: datetime) -> None`.
  - `User.reactivate(department_is_active: bool, department_has_active_manager: bool, now: datetime) -> None`.
  - `User.set_password(password_hash: PasswordHash, must_change: bool, now: datetime) -> None`.
  - `User.record_login(now: datetime) -> None`.
  - `User.update_profile(full_name: str | None, phone: str | None, now: datetime) -> None`.
  - `User.can_manage(other: "User") -> bool`.
  - Lỗi: `DepartmentRequiredError`, `AdminCannotHaveDepartmentError`, `DepartmentAlreadyHasManagerError`, `LastAdminCannotBeDeactivatedError`, `InactiveDepartmentError`, `EmptyFullNameError`, `CannotChangeToAdminError`.

**Ghi chú thiết kế:** mọi kiểm tra cần dữ liệu ngoài entity (`department_has_active_manager`, `is_last_active_admin`, `department_is_active`) đều nhận qua tham số. Use case tra cứu rồi truyền vào. Đây là cách giữ business rule trong domain mà không phá dependency rule.

- [ ] **Step 1: Viết test thất bại**

File `backend/tests/unit/identity/test_user.py`:

```python
from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.modules.identity.domain.entities.user import (
    AdminCannotHaveDepartmentError,
    CannotChangeToAdminError,
    DepartmentAlreadyHasManagerError,
    DepartmentRequiredError,
    EmptyFullNameError,
    InactiveDepartmentError,
    LastAdminCannotBeDeactivatedError,
    User,
)
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
SAU_DO = datetime(2026, 7, 21, 11, 0, tzinfo=UTC)
HASH_MAU = PasswordHash("$2b$12$hash_gia_lap")
PHONG_A: UUID = new_id()
PHONG_B: UUID = new_id()


def _tao_user(
    role: Role = Role.STAFF,
    department_id: UUID | None = PHONG_A,
    email: str = "nhanvien@congty.vn",
) -> User:
    return User.create(
        email=Email(email),
        password_hash=HASH_MAU,
        full_name="Nguyễn Văn A",
        role=role,
        department_id=department_id,
        now=BAY_GIO,
    )


class TestTaoUser:
    def test_staff_moi_o_trang_thai_hoat_dong_va_phai_doi_mat_khau(self) -> None:
        user = _tao_user()

        assert user.is_active is True
        assert user.must_change_password is True
        assert user.last_login_at is None
        assert user.department_id == PHONG_A

    def test_admin_khong_gan_phong_ban(self) -> None:
        admin = _tao_user(role=Role.ADMIN, department_id=None)

        assert admin.department_id is None

    @pytest.mark.parametrize("vai_tro", [Role.STAFF, Role.MANAGER])
    def test_staff_va_manager_thieu_phong_ban_thi_bi_tu_choi(self, vai_tro: Role) -> None:
        with pytest.raises(DepartmentRequiredError):
            _tao_user(role=vai_tro, department_id=None)

    def test_admin_co_phong_ban_thi_bi_tu_choi(self) -> None:
        with pytest.raises(AdminCannotHaveDepartmentError):
            _tao_user(role=Role.ADMIN, department_id=PHONG_A)

    @pytest.mark.parametrize("ten_sai", ["", "   "])
    def test_tu_choi_ho_ten_rong(self, ten_sai: str) -> None:
        with pytest.raises(EmptyFullNameError):
            User.create(
                email=Email("a@b.vn"),
                password_hash=HASH_MAU,
                full_name=ten_sai,
                role=Role.STAFF,
                department_id=PHONG_A,
                now=BAY_GIO,
            )


class TestDoiVaiTro:
    def test_staff_len_manager_khi_phong_chua_co_manager(self) -> None:
        user = _tao_user(role=Role.STAFF)

        user.change_role(
            new_role=Role.MANAGER,
            department_id=PHONG_A,
            department_has_active_manager=False,
            now=SAU_DO,
        )

        assert user.role is Role.MANAGER
        assert user.updated_at == SAU_DO

    def test_staff_len_manager_bi_tu_choi_khi_phong_da_co_manager(self) -> None:
        user = _tao_user(role=Role.STAFF)

        with pytest.raises(DepartmentAlreadyHasManagerError):
            user.change_role(
                new_role=Role.MANAGER,
                department_id=PHONG_A,
                department_has_active_manager=True,
                now=SAU_DO,
            )

        assert user.role is Role.STAFF

    def test_manager_xuong_staff_luon_duoc_phep(self) -> None:
        user = _tao_user(role=Role.MANAGER)

        user.change_role(
            new_role=Role.STAFF,
            department_id=PHONG_A,
            department_has_active_manager=True,
            now=SAU_DO,
        )

        assert user.role is Role.STAFF

    def test_khong_the_chuyen_thanh_admin(self) -> None:
        """Đề bài chỉ cho phép chuyển đổi Staff ↔ Manager."""
        user = _tao_user(role=Role.STAFF)

        with pytest.raises(CannotChangeToAdminError):
            user.change_role(
                new_role=Role.ADMIN,
                department_id=None,
                department_has_active_manager=False,
                now=SAU_DO,
            )

    def test_len_manager_o_phong_khac_thi_doi_luon_phong(self) -> None:
        user = _tao_user(role=Role.STAFF, department_id=PHONG_A)

        user.change_role(
            new_role=Role.MANAGER,
            department_id=PHONG_B,
            department_has_active_manager=False,
            now=SAU_DO,
        )

        assert user.department_id == PHONG_B


class TestChuyenPhongBan:
    def test_chuyen_staff_sang_phong_khac(self) -> None:
        user = _tao_user(role=Role.STAFF, department_id=PHONG_A)

        user.assign_to_department(
            department_id=PHONG_B, department_has_active_manager=False, now=SAU_DO
        )

        assert user.department_id == PHONG_B

    def test_chuyen_manager_sang_phong_da_co_manager_thi_bi_tu_choi(self) -> None:
        user = _tao_user(role=Role.MANAGER, department_id=PHONG_A)

        with pytest.raises(DepartmentAlreadyHasManagerError):
            user.assign_to_department(
                department_id=PHONG_B, department_has_active_manager=True, now=SAU_DO
            )

    def test_staff_khong_the_bo_trong_phong_ban(self) -> None:
        user = _tao_user(role=Role.STAFF)

        with pytest.raises(DepartmentRequiredError):
            user.assign_to_department(
                department_id=None, department_has_active_manager=False, now=SAU_DO
            )


class TestVoHieuHoa:
    def test_vo_hieu_hoa_staff(self) -> None:
        user = _tao_user()

        user.deactivate(is_last_active_admin=False, now=SAU_DO)

        assert user.is_active is False

    def test_khong_the_vo_hieu_hoa_admin_cuoi_cung(self) -> None:
        admin = _tao_user(role=Role.ADMIN, department_id=None)

        with pytest.raises(LastAdminCannotBeDeactivatedError):
            admin.deactivate(is_last_active_admin=True, now=SAU_DO)

        assert admin.is_active is True

    def test_vo_hieu_hoa_duoc_admin_khi_con_admin_khac(self) -> None:
        admin = _tao_user(role=Role.ADMIN, department_id=None)

        admin.deactivate(is_last_active_admin=False, now=SAU_DO)

        assert admin.is_active is False


class TestKichHoatLai:
    def test_kich_hoat_lai_staff(self) -> None:
        user = _tao_user()
        user.deactivate(is_last_active_admin=False, now=SAU_DO)

        user.reactivate(
            department_is_active=True, department_has_active_manager=False, now=SAU_DO
        )

        assert user.is_active is True

    def test_tu_choi_khi_phong_ban_da_bi_vo_hieu_hoa(self) -> None:
        user = _tao_user()
        user.deactivate(is_last_active_admin=False, now=SAU_DO)

        with pytest.raises(InactiveDepartmentError):
            user.reactivate(
                department_is_active=False, department_has_active_manager=False, now=SAU_DO
            )

    def test_tu_choi_kich_hoat_manager_khi_phong_da_co_manager_khac(self) -> None:
        manager = _tao_user(role=Role.MANAGER)
        manager.deactivate(is_last_active_admin=False, now=SAU_DO)

        with pytest.raises(DepartmentAlreadyHasManagerError):
            manager.reactivate(
                department_is_active=True, department_has_active_manager=True, now=SAU_DO
            )

    def test_kich_hoat_lai_admin_khong_can_phong_ban(self) -> None:
        admin = _tao_user(role=Role.ADMIN, department_id=None)
        admin.deactivate(is_last_active_admin=False, now=SAU_DO)

        admin.reactivate(
            department_is_active=False, department_has_active_manager=True, now=SAU_DO
        )

        assert admin.is_active is True


class TestMatKhauVaDangNhap:
    def test_dat_mat_khau_moi_tat_co_buoc_doi_mat_khau(self) -> None:
        user = _tao_user()
        hash_moi = PasswordHash("$2b$12$hash_moi")

        user.set_password(hash_moi, must_change=False, now=SAU_DO)

        assert user.password_hash == hash_moi
        assert user.must_change_password is False

    def test_admin_reset_mat_khau_thi_bat_buoc_doi_lai(self) -> None:
        user = _tao_user()
        user.set_password(PasswordHash("$2b$12$tam"), must_change=True, now=SAU_DO)

        assert user.must_change_password is True

    def test_ghi_nhan_lan_dang_nhap(self) -> None:
        user = _tao_user()

        user.record_login(now=SAU_DO)

        assert user.last_login_at == SAU_DO


class TestQuyenQuanLy:
    def test_admin_quan_ly_duoc_moi_nguoi(self) -> None:
        admin = _tao_user(role=Role.ADMIN, department_id=None, email="admin@congty.vn")
        staff = _tao_user(role=Role.STAFF, department_id=PHONG_A)

        assert admin.can_manage(staff) is True

    def test_manager_quan_ly_duoc_staff_cung_phong(self) -> None:
        manager = _tao_user(role=Role.MANAGER, department_id=PHONG_A, email="m@congty.vn")
        staff = _tao_user(role=Role.STAFF, department_id=PHONG_A)

        assert manager.can_manage(staff) is True

    def test_manager_khong_quan_ly_duoc_staff_phong_khac(self) -> None:
        manager = _tao_user(role=Role.MANAGER, department_id=PHONG_A, email="m@congty.vn")
        staff = _tao_user(role=Role.STAFF, department_id=PHONG_B)

        assert manager.can_manage(staff) is False

    def test_manager_khong_quan_ly_duoc_admin(self) -> None:
        manager = _tao_user(role=Role.MANAGER, department_id=PHONG_A, email="m@congty.vn")
        admin = _tao_user(role=Role.ADMIN, department_id=None, email="admin@congty.vn")

        assert manager.can_manage(admin) is False

    def test_manager_khong_quan_ly_duoc_manager_khac_cung_phong(self) -> None:
        """Quản lý chỉ quản được Nhân viên. Không có quyền lên nhau, kể cả cùng
        phòng ban — thiếu test này thì lỗi ``other.role is not Role.ADMIN`` sẽ
        lọt qua và biến can_manage thành lỗ hổng leo thang quyền."""
        manager_a = _tao_user(role=Role.MANAGER, department_id=PHONG_A, email="ma@congty.vn")
        manager_b = _tao_user(role=Role.MANAGER, department_id=PHONG_A, email="mb@congty.vn")

        assert manager_a.can_manage(manager_b) is False

    def test_staff_khong_quan_ly_duoc_ai(self) -> None:
        staff = _tao_user(role=Role.STAFF, department_id=PHONG_A)
        khac = _tao_user(role=Role.STAFF, department_id=PHONG_A, email="b@congty.vn")

        assert staff.can_manage(khac) is False


class TestChanChuyenTuAdmin:
    def test_khong_ha_duoc_admin_xuong_staff(self) -> None:
        """Chỉ chuyển đổi Staff ↔ Manager. Guard tự-chặn của Admin (nhánh
        ``self.role is Role.ADMIN``) chỉ được kiểm chứng bởi test này."""
        admin = _tao_user(role=Role.ADMIN, department_id=None, email="admin@congty.vn")

        with pytest.raises(CannotChangeToAdminError):
            admin.change_role(
                new_role=Role.STAFF,
                department_id=PHONG_A,
                department_has_active_manager=False,
                now=SAU_DO,
            )


class TestCapNhatHoSo:
    def test_cap_nhat_ho_ten_va_so_dien_thoai(self) -> None:
        user = _tao_user()

        user.update_profile(full_name="Tên Mới", phone="0912345678", now=SAU_DO)

        assert user.full_name == "Tên Mới"
        assert user.phone == "0912345678"
        assert user.updated_at == SAU_DO

    def test_tham_so_none_giu_nguyen_gia_tri_cu(self) -> None:
        """``None`` nghĩa là không đổi trường đó — không phải xoá trắng nó."""
        user = _tao_user()
        ho_ten_cu = user.full_name

        user.update_profile(full_name=None, phone="0900000000", now=SAU_DO)

        assert user.full_name == ho_ten_cu
        assert user.phone == "0900000000"

    def test_tu_choi_ho_ten_rong(self) -> None:
        user = _tao_user()

        with pytest.raises(EmptyFullNameError):
            user.update_profile(full_name="   ", phone=None, now=SAU_DO)
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/unit/identity/test_user.py -v
```

Expected: FAIL với `ModuleNotFoundError` cho `src.modules.identity.domain.entities.user`.

- [ ] **Step 3: Viết `user.py`**

```python
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

    def set_password(
        self, password_hash: PasswordHash, must_change: bool, now: datetime
    ) -> None:
        """Đặt mật khẩu mới.

        ``must_change=True`` khi Admin cấp mật khẩu tạm; ``False`` khi chính
        người dùng tự đổi.
        """
        self.password_hash = password_hash
        self.must_change_password = must_change
        self.updated_at = now

    def record_login(self, now: datetime) -> None:
        self.last_login_at = now

    def update_profile(
        self, full_name: str | None, phone: str | None, now: datetime
    ) -> None:
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
```

- [ ] **Step 4: Chạy test để xác nhận thành công**

```bash
uv run pytest tests/unit/identity/test_user.py -v
```

Expected: `28 passed`.

- [ ] **Step 5: Kiểm tra chất lượng mã**

```bash
uv run mypy src
uv run ruff check .
uv run lint-imports
```

Expected: xanh.

- [ ] **Step 6: Commit**

```bash
git add backend/src/modules/identity/domain/entities/user.py backend/tests/unit/identity/test_user.py
git commit -m "feat: add user entity with role, department, and lifecycle rules"
```

---

## Task 7: Entity `RefreshToken` và `AuditLog`

**Files:**
- Create: `backend/src/modules/identity/domain/entities/refresh_token.py`
- Create: `backend/src/modules/identity/domain/entities/audit_log.py`
- Test: `backend/tests/unit/identity/test_refresh_token.py`
- Test: `backend/tests/unit/identity/test_audit_log.py`

**Interfaces:**
- Consumes: `AggregateRoot`, `BusinessRuleViolationError`.
- Produces:
  - `RefreshToken` — trường: `id: UUID`, `user_id: UUID`, `token_hash: str`, `expires_at: datetime`, `revoked_at: datetime | None`, `replaced_by_id: UUID | None`, `user_agent: str | None`, `ip_address: str | None`, `created_at: datetime`.
  - `RefreshToken.issue(user_id, token_hash, expires_at, now, user_agent=None, ip_address=None) -> RefreshToken`.
  - `RefreshToken.is_valid(now: datetime) -> bool` — chưa thu hồi và chưa hết hạn.
  - `RefreshToken.is_expired(now: datetime) -> bool`.
  - `RefreshToken.is_revoked() -> bool`.
  - `RefreshToken.revoke(now: datetime) -> None` — gọi lại lần nữa không đổi `revoked_at`.
  - `RefreshToken.rotate_to(new_token_id: UUID, now: datetime) -> None` — thu hồi và ghi `replaced_by_id`.
  - `AuditAction` — `StrEnum` với các giá trị: `USER_CREATED`, `USER_UPDATED`, `USER_DEACTIVATED`, `USER_REACTIVATED`, `USER_ROLE_CHANGED`, `USER_DEPARTMENT_CHANGED`, `USER_PASSWORD_RESET`, `USER_PASSWORD_CHANGED`, `DEPARTMENT_CREATED`, `DEPARTMENT_UPDATED`, `DEPARTMENT_DEACTIVATED`, `AUTH_LOGIN_SUCCEEDED`, `AUTH_LOGIN_FAILED`, `AUTH_LOGOUT`, `AUTH_TOKEN_REUSE_DETECTED`.
  - `AuditLog.record(action, actor_id, resource_type, resource_id, now, changes=None, ip_address=None, user_agent=None) -> AuditLog`.

**Ghi chú thiết kế:** `AuditLog` là bản ghi chỉ ghi thêm, không có phương thức sửa hay xoá. Đó là điểm mấu chốt để nhật ký đáng tin cậy.

- [ ] **Step 1: Viết test cho `RefreshToken`**

File `backend/tests/unit/identity/test_refresh_token.py`:

```python
from datetime import UTC, datetime, timedelta

from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
USER_ID = new_id()


def _cap_token(het_han_sau: timedelta = timedelta(days=7)) -> RefreshToken:
    return RefreshToken.issue(
        user_id=USER_ID,
        token_hash="hash_gia_lap",
        expires_at=BAY_GIO + het_han_sau,
        now=BAY_GIO,
    )


class TestCapToken:
    def test_token_moi_con_hieu_luc(self) -> None:
        token = _cap_token()

        assert token.is_valid(now=BAY_GIO) is True
        assert token.is_revoked() is False
        assert token.revoked_at is None
        assert token.replaced_by_id is None


class TestHetHan:
    def test_token_het_han_thi_khong_con_hieu_luc(self) -> None:
        token = _cap_token(het_han_sau=timedelta(days=7))
        sau_khi_het_han = BAY_GIO + timedelta(days=8)

        assert token.is_expired(now=sau_khi_het_han) is True
        assert token.is_valid(now=sau_khi_het_han) is False

    def test_dung_thoi_diem_het_han_thi_coi_la_het_han(self) -> None:
        token = _cap_token(het_han_sau=timedelta(days=7))
        dung_luc_het_han = BAY_GIO + timedelta(days=7)

        assert token.is_expired(now=dung_luc_het_han) is True


class TestThuHoi:
    def test_thu_hoi_lam_token_mat_hieu_luc(self) -> None:
        token = _cap_token()
        luc_thu_hoi = BAY_GIO + timedelta(hours=1)

        token.revoke(now=luc_thu_hoi)

        assert token.is_revoked() is True
        assert token.is_valid(now=luc_thu_hoi) is False
        assert token.revoked_at == luc_thu_hoi

    def test_thu_hoi_lan_hai_khong_doi_moc_thoi_gian(self) -> None:
        token = _cap_token()
        lan_dau = BAY_GIO + timedelta(hours=1)
        lan_hai = BAY_GIO + timedelta(hours=2)

        token.revoke(now=lan_dau)
        token.revoke(now=lan_hai)

        assert token.revoked_at == lan_dau


class TestXoayToken:
    def test_xoay_token_thu_hoi_ban_cu_va_ghi_lai_ban_moi(self) -> None:
        token = _cap_token()
        token_moi_id = new_id()
        luc_xoay = BAY_GIO + timedelta(hours=1)

        token.rotate_to(new_token_id=token_moi_id, now=luc_xoay)

        assert token.is_revoked() is True
        assert token.replaced_by_id == token_moi_id
        assert token.revoked_at == luc_xoay

    def test_token_da_xoay_thi_khong_con_hieu_luc(self) -> None:
        token = _cap_token()

        token.rotate_to(new_token_id=new_id(), now=BAY_GIO)

        assert token.is_valid(now=BAY_GIO) is False
```

- [ ] **Step 2: Viết test cho `AuditLog`**

File `backend/tests/unit/identity/test_audit_log.py`:

```python
from datetime import UTC, datetime

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


def test_ghi_nhan_hanh_dong_kem_day_du_thong_tin() -> None:
    actor_id = new_id()
    resource_id = new_id()

    ban_ghi = AuditLog.record(
        action=AuditAction.USER_CREATED,
        actor_id=actor_id,
        resource_type="user",
        resource_id=str(resource_id),
        now=BAY_GIO,
        changes={"email": "moi@congty.vn"},
        ip_address="10.0.0.1",
    )

    assert ban_ghi.action is AuditAction.USER_CREATED
    assert ban_ghi.actor_id == actor_id
    assert ban_ghi.resource_type == "user"
    assert ban_ghi.resource_id == str(resource_id)
    assert ban_ghi.changes == {"email": "moi@congty.vn"}
    assert ban_ghi.ip_address == "10.0.0.1"
    assert ban_ghi.created_at == BAY_GIO


def test_hanh_dong_cua_he_thong_khong_can_actor() -> None:
    ban_ghi = AuditLog.record(
        action=AuditAction.AUTH_LOGIN_FAILED,
        actor_id=None,
        resource_type="auth",
        resource_id=None,
        now=BAY_GIO,
    )

    assert ban_ghi.actor_id is None
    assert ban_ghi.resource_id is None


def test_audit_log_khong_co_phuong_thuc_sua_hay_xoa() -> None:
    """Nhật ký chỉ được ghi thêm — đó là điều làm nó đáng tin cậy."""
    ten_phuong_thuc = {t for t in dir(AuditLog) if not t.startswith("_")}

    assert not ten_phuong_thuc & {"update", "modify", "delete", "edit"}


def test_moi_hanh_dong_deu_co_ma_dang_chu_thuong_gach_cham() -> None:
    for hanh_dong in AuditAction:
        assert hanh_dong.value.islower()
        assert "." in hanh_dong.value
```

- [ ] **Step 3: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/unit/identity/test_refresh_token.py tests/unit/identity/test_audit_log.py -v
```

Expected: FAIL với `ModuleNotFoundError`.

- [ ] **Step 4: Viết `refresh_token.py`**

```python
"""Entity refresh token."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.shared.domain.entity import AggregateRoot
from src.shared.domain.identifiers import new_id


@dataclass(eq=False, kw_only=True)
class RefreshToken(AggregateRoot):
    """Một refresh token đã cấp cho người dùng.

    Chỉ lưu hash của token, không lưu token thô — kẻ đọc được cơ sở dữ liệu
    vẫn không mạo danh được người dùng.

    ``replaced_by_id`` tạo thành chuỗi token nối tiếp nhau. Khi một token đã
    bị thay thế lại được gửi lên, hệ thống hiểu là token bị đánh cắp và thu hồi
    toàn bộ chuỗi.
    """

    user_id: UUID
    token_hash: str
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None = None
    replaced_by_id: UUID | None = None
    user_agent: str | None = None
    ip_address: str | None = None

    @classmethod
    def issue(
        cls,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> "RefreshToken":
        return cls(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
            replaced_by_id=None,
            user_agent=user_agent,
            ip_address=ip_address,
            created_at=now,
        )

    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def is_valid(self, now: datetime) -> bool:
        return not self.is_revoked() and not self.is_expired(now)

    def revoke(self, now: datetime) -> None:
        """Thu hồi token. Gọi lại lần nữa không làm thay đổi mốc thu hồi ban đầu."""
        if self.revoked_at is None:
            self.revoked_at = now

    def rotate_to(self, new_token_id: UUID, now: datetime) -> None:
        """Thu hồi token này và ghi nhận token thay thế nó."""
        self.revoke(now)
        self.replaced_by_id = new_token_id
```

**Lưu ý về `kw_only=True`:** `Entity` khai báo `id` có giá trị mặc định. Trong dataclass thông thường, điều đó buộc **mọi trường khai báo sau nó cũng phải có mặc định** — kể cả ở lớp con — nếu không sẽ gặp `TypeError: non-default argument follows default argument` ngay lúc import.

`kw_only=True` gỡ ràng buộc đó: tham số chỉ-theo-tên không có thứ tự nên trường bắt buộc đứng sau trường có mặc định là hợp lệ. Nhờ vậy `user_id`, `token_hash`, `expires_at` khai báo đúng bản chất nghiệp vụ là bắt buộc, thay vì mang giá trị mặc định giả mà mọi factory đều phải ghi đè.

Đánh đổi: mọi lời gọi phải dùng tham số tên — `RefreshToken(user_id=..., token_hash=...)`, không dùng được `RefreshToken(uid, hash)`. Toàn bộ code trong plan vốn đã viết theo kiểu này.

Quy tắc tương tự áp dụng cho `User`, `Department` và `AuditLog`.

- [ ] **Step 5: Viết `audit_log.py`**

```python
"""Entity bản ghi nhật ký kiểm toán."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from src.shared.domain.entity import Entity


class AuditAction(StrEnum):
    """Các hành động được ghi nhật ký.

    Giá trị dùng dạng ``<đối tượng>.<hành động>`` để lọc theo tiền tố khi
    tra cứu, ví dụ mọi hành động xác thực đều bắt đầu bằng ``auth.``.
    """

    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DEACTIVATED = "user.deactivated"
    USER_REACTIVATED = "user.reactivated"
    USER_ROLE_CHANGED = "user.role_changed"
    USER_DEPARTMENT_CHANGED = "user.department_changed"
    USER_PASSWORD_RESET = "user.password_reset"
    USER_PASSWORD_CHANGED = "user.password_changed"

    DEPARTMENT_CREATED = "department.created"
    DEPARTMENT_UPDATED = "department.updated"
    DEPARTMENT_DEACTIVATED = "department.deactivated"

    AUTH_LOGIN_SUCCEEDED = "auth.login_succeeded"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_REUSE_DETECTED = "auth.token_reuse_detected"


@dataclass(eq=False, kw_only=True)
class AuditLog(Entity):
    """Bản ghi một hành động đã xảy ra trong hệ thống.

    Chỉ ghi thêm: entity này cố ý không có phương thức sửa hay xoá.
    """

    action: AuditAction
    resource_type: str
    created_at: datetime
    actor_id: UUID | None = None
    resource_id: str | None = None
    changes: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    @classmethod
    def record(
        cls,
        action: AuditAction,
        actor_id: UUID | None,
        resource_type: str,
        resource_id: str | None,
        now: datetime,
        changes: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> "AuditLog":
        """Tạo bản ghi nhật ký.

        ``actor_id`` là ``None`` khi hành động do hệ thống thực hiện hoặc khi
        chưa xác định được người gọi, ví dụ đăng nhập thất bại.
        """
        return cls(
            action=action,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
        )
```

- [ ] **Step 6: Chạy test để xác nhận thành công**

```bash
uv run pytest tests/unit/identity -v
```

Expected: toàn bộ test của Task 4–7 xanh, tổng `70 passed`.

- [ ] **Step 7: Kiểm tra chất lượng mã**

```bash
uv run mypy src
uv run ruff check .
uv run lint-imports
```

Expected: xanh.

- [ ] **Step 8: Commit**

```bash
git add backend/src/modules/identity/domain/entities backend/tests/unit/identity
git commit -m "feat: add refresh token and audit log entities"
```

---

## Task 8: Interface repository

**Files:**
- Create: `backend/src/modules/identity/domain/repositories/__init__.py`
- Create: `backend/src/modules/identity/domain/repositories/user_repository.py`
- Create: `backend/src/modules/identity/domain/repositories/department_repository.py`
- Create: `backend/src/modules/identity/domain/repositories/refresh_token_repository.py`
- Create: `backend/src/modules/identity/domain/repositories/audit_log_repository.py`
- Test: `backend/tests/unit/identity/fakes.py`
- Test: `backend/tests/unit/identity/test_fakes.py`

**Interfaces:**
- Consumes: các entity từ Task 5–7.
- Produces (mọi phương thức đều `async`):
  - `IUserRepository`: `get_by_id(user_id: UUID) -> User | None`; `get_by_email(email: Email) -> User | None`; `add(user: User) -> None`; `update(user: User) -> None`; `list_users(department_id: UUID | None, role: Role | None, is_active: bool | None, search: str | None, limit: int, offset: int) -> list[User]`; `count_users(department_id: UUID | None, role: Role | None, is_active: bool | None, search: str | None) -> int`; `count_active_in_department(department_id: UUID) -> int`; `has_active_manager(department_id: UUID, exclude_user_id: UUID | None) -> bool`; `count_active_admins() -> int`.
  - `IDepartmentRepository`: `get_by_id(department_id: UUID) -> Department | None`; `get_by_name(name: str) -> Department | None`; `add(department: Department) -> None`; `update(department: Department) -> None`; `list_departments(is_active: bool | None, limit: int, offset: int) -> list[Department]`; `count_departments(is_active: bool | None) -> int`.
  - `IRefreshTokenRepository`: `get_by_hash(token_hash: str) -> RefreshToken | None`; `add(token: RefreshToken) -> None`; `update(token: RefreshToken) -> None`; `revoke_all_for_user(user_id: UUID, now: datetime) -> None`; `revoke_chain(token: RefreshToken, now: datetime) -> None`.
  - `IAuditLogRepository`: `add(entry: AuditLog) -> None`; `list_entries(actor_id: UUID | None, action: AuditAction | None, resource_type: str | None, from_time: datetime | None, to_time: datetime | None, limit: int, offset: int) -> list[AuditLog]`; `count_entries(actor_id: UUID | None, action: AuditAction | None, resource_type: str | None, from_time: datetime | None, to_time: datetime | None) -> int`.
  - Fake in-memory: `FakeUserRepository`, `FakeDepartmentRepository`, `FakeRefreshTokenRepository`, `FakeAuditLogRepository`, `FakeClock` — dùng cho mọi unit test use case ở Task 13–15.

**Ghi chú thiết kế:** interface đặt trong `domain/` còn implementation ở `infrastructure/` — đây chính là chỗ đảo ngược phụ thuộc, giúp `domain` không biết gì về SQLAlchemy.

Các fake in-memory được viết ngay tại task này để Task 13–15 có sẵn công cụ test. Fake phản ánh hành vi thật; thư viện mock chỉ phản ánh giả định của người viết test.

- [ ] **Step 1: Viết `user_repository.py`**

```python
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
```

- [ ] **Step 2: Viết `department_repository.py`**

```python
"""Interface repository cho phòng ban."""

from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.entities.department import Department


class IDepartmentRepository(Protocol):
    """Truy xuất và lưu trữ phòng ban."""

    async def get_by_id(self, department_id: UUID) -> Department | None: ...

    async def get_by_name(self, name: str) -> Department | None:
        """Tìm theo tên, không phân biệt hoa thường, chỉ trong phòng đang hoạt động."""
        ...

    async def add(self, department: Department) -> None: ...

    async def update(self, department: Department) -> None: ...

    async def list_departments(
        self,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Department]: ...

    async def count_departments(self, is_active: bool | None = None) -> int: ...
```

- [ ] **Step 3: Viết `refresh_token_repository.py`**

```python
"""Interface repository cho refresh token."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.entities.refresh_token import RefreshToken


class IRefreshTokenRepository(Protocol):
    """Truy xuất và lưu trữ refresh token."""

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    async def add(self, token: RefreshToken) -> None: ...

    async def update(self, token: RefreshToken) -> None: ...

    async def revoke_all_for_user(self, user_id: UUID, now: datetime) -> None:
        """Thu hồi mọi token còn hiệu lực của một người dùng.

        Dùng khi vô hiệu hoá tài khoản hoặc khi đổi mật khẩu.
        """
        ...

    async def revoke_chain(self, token: RefreshToken, now: datetime) -> None:
        """Thu hồi toàn bộ chuỗi token nối với ``token`` qua ``replaced_by_id``.

        Dùng khi phát hiện một token đã bị thay thế lại được gửi lên — dấu hiệu
        token đã bị đánh cắp.
        """
        ...
```

- [ ] **Step 4: Viết `audit_log_repository.py`**

```python
"""Interface repository cho nhật ký kiểm toán."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog


class IAuditLogRepository(Protocol):
    """Ghi và tra cứu nhật ký kiểm toán."""

    async def add(self, entry: AuditLog) -> None: ...

    async def list_entries(
        self,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Danh sách bản ghi, mới nhất trước."""
        ...

    async def count_entries(
        self,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> int: ...
```

- [ ] **Step 5: Viết fake in-memory**

File `backend/tests/unit/identity/fakes.py`:

```python
"""Repository giả lập trong bộ nhớ, dùng cho unit test use case.

Fake phản ánh hành vi thật của repository; thư viện mock chỉ phản ánh giả định
của người viết test. Khi hành vi thật thay đổi, fake sai sẽ làm test đỏ — mock
thì không.
"""

from datetime import UTC, datetime
from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.role import Role


class FakeClock:
    """Đồng hồ do test điều khiển."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 7, 21, 10, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, **khoang_thoi_gian: float) -> None:
        from datetime import timedelta

        self._now += timedelta(**khoang_thoi_gian)


class FakeUserRepository:
    """Lưu người dùng trong một dict."""

    def __init__(self, users: list[User] | None = None) -> None:
        self._users: dict[UUID, User] = {u.id: u for u in (users or [])}

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    async def get_by_email(self, email: Email) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def add(self, user: User) -> None:
        self._users[user.id] = user

    async def update(self, user: User) -> None:
        self._users[user.id] = user

    def _loc(
        self,
        department_id: UUID | None,
        role: Role | None,
        is_active: bool | None,
        search: str | None,
    ) -> list[User]:
        ket_qua = list(self._users.values())
        if department_id is not None:
            ket_qua = [u for u in ket_qua if u.department_id == department_id]
        if role is not None:
            ket_qua = [u for u in ket_qua if u.role is role]
        if is_active is not None:
            ket_qua = [u for u in ket_qua if u.is_active is is_active]
        if search:
            tu_khoa = search.lower()
            ket_qua = [
                u
                for u in ket_qua
                if tu_khoa in u.full_name.lower() or tu_khoa in u.email.value
            ]
        return sorted(ket_qua, key=lambda u: u.created_at)

    async def list_users(
        self,
        department_id: UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        return self._loc(department_id, role, is_active, search)[offset : offset + limit]

    async def count_users(
        self,
        department_id: UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> int:
        return len(self._loc(department_id, role, is_active, search))

    async def count_active_in_department(self, department_id: UUID) -> int:
        return len(
            [
                u
                for u in self._users.values()
                if u.department_id == department_id and u.is_active
            ]
        )

    async def has_active_manager(
        self, department_id: UUID, exclude_user_id: UUID | None = None
    ) -> bool:
        return any(
            u.department_id == department_id
            and u.role is Role.MANAGER
            and u.is_active
            and u.id != exclude_user_id
            for u in self._users.values()
        )

    async def count_active_admins(self) -> int:
        return len(
            [u for u in self._users.values() if u.role is Role.ADMIN and u.is_active]
        )


class FakeDepartmentRepository:
    """Lưu phòng ban trong một dict."""

    def __init__(self, departments: list[Department] | None = None) -> None:
        self._departments: dict[UUID, Department] = {
            d.id: d for d in (departments or [])
        }

    async def get_by_id(self, department_id: UUID) -> Department | None:
        return self._departments.get(department_id)

    async def get_by_name(self, name: str) -> Department | None:
        for phong in self._departments.values():
            if phong.name.lower() == name.strip().lower() and phong.is_active:
                return phong
        return None

    async def add(self, department: Department) -> None:
        self._departments[department.id] = department

    async def update(self, department: Department) -> None:
        self._departments[department.id] = department

    async def list_departments(
        self,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Department]:
        ket_qua = list(self._departments.values())
        if is_active is not None:
            ket_qua = [d for d in ket_qua if d.is_active is is_active]
        ket_qua.sort(key=lambda d: d.name)
        return ket_qua[offset : offset + limit]

    async def count_departments(self, is_active: bool | None = None) -> int:
        ket_qua = list(self._departments.values())
        if is_active is not None:
            ket_qua = [d for d in ket_qua if d.is_active is is_active]
        return len(ket_qua)


class FakeRefreshTokenRepository:
    """Lưu refresh token trong một dict."""

    def __init__(self) -> None:
        self._tokens: dict[UUID, RefreshToken] = {}

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        for token in self._tokens.values():
            if token.token_hash == token_hash:
                return token
        return None

    async def add(self, token: RefreshToken) -> None:
        self._tokens[token.id] = token

    async def update(self, token: RefreshToken) -> None:
        self._tokens[token.id] = token

    async def revoke_all_for_user(self, user_id: UUID, now: datetime) -> None:
        for token in self._tokens.values():
            if token.user_id == user_id and not token.is_revoked():
                token.revoke(now)

    async def revoke_chain(self, token: RefreshToken, now: datetime) -> None:
        hien_tai: RefreshToken | None = token
        da_duyet: set[UUID] = set()
        while hien_tai is not None and hien_tai.id not in da_duyet:
            da_duyet.add(hien_tai.id)
            hien_tai.revoke(now)
            ke_tiep_id = hien_tai.replaced_by_id
            hien_tai = self._tokens.get(ke_tiep_id) if ke_tiep_id else None


class FakeAuditLogRepository:
    """Lưu bản ghi nhật ký trong một danh sách."""

    def __init__(self) -> None:
        self.entries: list[AuditLog] = []

    async def add(self, entry: AuditLog) -> None:
        self.entries.append(entry)

    def _loc(
        self,
        actor_id: UUID | None,
        action: AuditAction | None,
        resource_type: str | None,
        from_time: datetime | None,
        to_time: datetime | None,
    ) -> list[AuditLog]:
        ket_qua = list(self.entries)
        if actor_id is not None:
            ket_qua = [e for e in ket_qua if e.actor_id == actor_id]
        if action is not None:
            ket_qua = [e for e in ket_qua if e.action is action]
        if resource_type is not None:
            ket_qua = [e for e in ket_qua if e.resource_type == resource_type]
        if from_time is not None:
            ket_qua = [e for e in ket_qua if e.created_at >= from_time]
        if to_time is not None:
            ket_qua = [e for e in ket_qua if e.created_at <= to_time]
        return sorted(ket_qua, key=lambda e: e.created_at, reverse=True)

    async def list_entries(
        self,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        ket_qua = self._loc(actor_id, action, resource_type, from_time, to_time)
        return ket_qua[offset : offset + limit]

    async def count_entries(
        self,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> int:
        return len(self._loc(actor_id, action, resource_type, from_time, to_time))
```

- [ ] **Step 6: Viết test cho chính các fake**

File `backend/tests/unit/identity/test_fakes.py`:

```python
"""Fake cũng cần test — fake sai sẽ làm mọi test dùng nó trở nên vô nghĩa."""

from datetime import UTC, datetime

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.shared.domain.identifiers import new_id
from tests.unit.identity.fakes import (
    FakeDepartmentRepository,
    FakeRefreshTokenRepository,
    FakeUserRepository,
)

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
PHONG_A = new_id()
PHONG_B = new_id()


def _user(role: Role, department_id, email: str, is_active: bool = True) -> User:
    u = User.create(
        email=Email(email),
        password_hash=PasswordHash("$2b$12$x"),
        full_name="Người dùng",
        role=role,
        department_id=department_id,
        now=BAY_GIO,
    )
    if not is_active:
        u.deactivate(is_last_active_admin=False, now=BAY_GIO)
    return u


async def test_tim_duoc_user_theo_email_khong_phan_biet_hoa_thuong() -> None:
    repo = FakeUserRepository([_user(Role.STAFF, PHONG_A, "a@congty.vn")])

    assert await repo.get_by_email(Email("A@CONGTY.VN")) is not None


async def test_dem_dung_nhan_vien_dang_hoat_dong_trong_phong() -> None:
    repo = FakeUserRepository(
        [
            _user(Role.STAFF, PHONG_A, "a@congty.vn"),
            _user(Role.STAFF, PHONG_A, "b@congty.vn", is_active=False),
            _user(Role.STAFF, PHONG_B, "c@congty.vn"),
        ]
    )

    assert await repo.count_active_in_department(PHONG_A) == 1


async def test_has_active_manager_bo_qua_chinh_nguoi_dang_sua() -> None:
    manager = _user(Role.MANAGER, PHONG_A, "m@congty.vn")
    repo = FakeUserRepository([manager])

    assert await repo.has_active_manager(PHONG_A) is True
    assert await repo.has_active_manager(PHONG_A, exclude_user_id=manager.id) is False


async def test_has_active_manager_bo_qua_manager_da_vo_hieu_hoa() -> None:
    repo = FakeUserRepository([_user(Role.MANAGER, PHONG_A, "m@congty.vn", is_active=False)])

    assert await repo.has_active_manager(PHONG_A) is False


async def test_tim_kiem_khop_ca_ho_ten_va_email() -> None:
    repo = FakeUserRepository([_user(Role.STAFF, PHONG_A, "nguyenvana@congty.vn")])

    assert len(await repo.list_users(search="NGUYENVANA")) == 1
    assert len(await repo.list_users(search="Người")) == 1
    assert len(await repo.list_users(search="khong-ton-tai")) == 0


async def test_get_by_name_bo_qua_phong_ban_da_vo_hieu_hoa() -> None:
    phong = Department.create(name="Kinh doanh", description=None, now=BAY_GIO)
    phong.deactivate(active_member_count=0, now=BAY_GIO)
    repo = FakeDepartmentRepository([phong])

    assert await repo.get_by_name("Kinh doanh") is None


async def test_revoke_chain_thu_hoi_toan_bo_chuoi_token() -> None:
    repo = FakeRefreshTokenRepository()
    dau = RefreshToken.issue(new_id(), "hash1", BAY_GIO, BAY_GIO)
    giua = RefreshToken.issue(new_id(), "hash2", BAY_GIO, BAY_GIO)
    cuoi = RefreshToken.issue(new_id(), "hash3", BAY_GIO, BAY_GIO)
    dau.rotate_to(giua.id, BAY_GIO)
    giua.rotate_to(cuoi.id, BAY_GIO)
    for t in (dau, giua, cuoi):
        await repo.add(t)

    await repo.revoke_chain(dau, now=BAY_GIO)

    assert cuoi.is_revoked() is True
```

- [ ] **Step 7: Chạy toàn bộ test unit**

```bash
cd backend
mkdir -p src/modules/identity/domain/repositories
touch src/modules/identity/domain/repositories/__init__.py
uv run pytest tests/unit -v
```

Expected: toàn bộ test unit xanh (con số tích luỹ tăng dần qua các task).

- [ ] **Step 8: Kiểm tra chất lượng mã và dependency rule**

```bash
uv run mypy src
uv run ruff check .
uv run lint-imports
```

Expected: `Contracts: 3 kept, 0 broken.`

- [ ] **Step 9: Đo coverage của tầng domain**

```bash
uv run pytest tests/unit --cov=src/modules/identity/domain --cov=src/shared/domain --cov-report=term-missing
```

Expected: coverage ≥ 90% cho cả hai gói.

- [ ] **Step 10: Commit**

```bash
git add backend/src/modules/identity/domain/repositories backend/tests/unit/identity
git commit -m "feat: add repository interfaces and in-memory fakes for testing"
```

---

## Tiếp theo

- [Phần 3 — Hạ tầng lưu trữ](2026-07-21-omnichat-foundation-part3-infra.md) (Task 9–12)
