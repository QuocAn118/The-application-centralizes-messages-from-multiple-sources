# OmniChat Foundation — Phần 3: Hạ tầng lưu trữ (Task 9–12)

> Tiếp nối [phần 2](2026-07-21-omnichat-foundation-part2-domain.md). Global Constraints ở [phần 1](2026-07-21-omnichat-foundation.md) áp dụng cho mọi task tại đây.

Giai đoạn này nối tầng domain với PostgreSQL. Mọi test ở đây là integration test chạy trên cơ sở dữ liệu thật.

---

## Task 9: ORM model và migration đầu tiên

**Files:**
- Create: `backend/src/modules/identity/infrastructure/__init__.py`
- Create: `backend/src/modules/identity/infrastructure/models/__init__.py`
- Create: `backend/src/modules/identity/infrastructure/models/department_model.py`
- Create: `backend/src/modules/identity/infrastructure/models/user_model.py`
- Create: `backend/src/modules/identity/infrastructure/models/refresh_token_model.py`
- Create: `backend/src/modules/identity/infrastructure/models/audit_log_model.py`
- Modify: `backend/migrations/env.py` — thêm import ORM model
- Create: `backend/migrations/versions/<hash>_tao_bang_identity.py` (sinh tự động)
- Test: `backend/tests/integration/test_schema.py`

**Interfaces:**
- Consumes: `Base` từ Task 3.
- Produces:
  - `DepartmentModel` — bảng `departments`.
  - `UserModel` — bảng `users`.
  - `RefreshTokenModel` — bảng `refresh_tokens`.
  - `AuditLogModel` — bảng `audit_logs`.
  - Migration tạo bốn bảng cùng toàn bộ index và constraint.

**Ghi chú thiết kế:** ORM model chỉ mô tả bảng, không chứa business logic. Chúng cố ý không có phương thức nào — mọi hành vi nằm ở domain entity.

- [ ] **Step 1: Viết test kiểm tra schema**

File `backend/tests/integration/test_schema.py`:

```python
"""Kiểm tra schema thật trong PostgreSQL, không chỉ kiểm tra khai báo Python.

Các ràng buộc quan trọng nhất của hệ thống nằm ở tầng cơ sở dữ liệu; test này
xác nhận chúng thực sự tồn tại và thực sự có hiệu lực.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


async def _them_phong_ban(session: AsyncSession, ten: str) -> str:
    ket_qua = await session.execute(
        text(
            "INSERT INTO departments (id, name, description, is_active, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :ten, NULL, true, :bg, :bg) RETURNING id"
        ),
        {"ten": ten, "bg": BAY_GIO},
    )
    return str(ket_qua.scalar_one())


async def _them_user(
    session: AsyncSession,
    email: str,
    role: str,
    department_id: str | None,
    is_active: bool = True,
) -> str:
    ket_qua = await session.execute(
        text(
            "INSERT INTO users (id, email, password_hash, full_name, phone, role, "
            "department_id, is_active, must_change_password, last_login_at, "
            "created_at, updated_at) "
            "VALUES (gen_random_uuid(), :email, 'hash', 'Ho Ten', NULL, :role, "
            ":dept, :active, true, NULL, :bg, :bg) RETURNING id"
        ),
        {
            "email": email,
            "role": role,
            "dept": department_id,
            "active": is_active,
            "bg": BAY_GIO,
        },
    )
    return str(ket_qua.scalar_one())


class TestBangTonTai:
    @pytest.mark.parametrize(
        "ten_bang", ["departments", "users", "refresh_tokens", "audit_logs"]
    )
    async def test_bang_da_duoc_tao(self, db_session: AsyncSession, ten_bang: str) -> None:
        ket_qua = await db_session.execute(
            text("SELECT to_regclass(:ten) IS NOT NULL"), {"ten": f"public.{ten_bang}"}
        )

        assert ket_qua.scalar_one() is True


class TestRangBuocEmail:
    async def test_email_trung_bi_tu_choi(self, db_session: AsyncSession) -> None:
        phong = await _them_phong_ban(db_session, "Phong Email 1")
        await _them_user(db_session, "trung@congty.vn", "STAFF", phong)

        with pytest.raises(IntegrityError):
            await _them_user(db_session, "trung@congty.vn", "STAFF", phong)

    async def test_email_khac_kieu_chu_van_bi_coi_la_trung(
        self, db_session: AsyncSession
    ) -> None:
        """Index đặt trên lower(email) nên hoa thường không tạo ra bản ghi mới."""
        phong = await _them_phong_ban(db_session, "Phong Email 2")
        await _them_user(db_session, "hoathuong@congty.vn", "STAFF", phong)

        with pytest.raises(IntegrityError):
            await _them_user(db_session, "HoaThuong@CongTy.VN", "STAFF", phong)

    async def test_user_da_vo_hieu_hoa_van_giu_email(
        self, db_session: AsyncSession
    ) -> None:
        """Email duy nhất vĩnh viễn — kể cả khi tài khoản đã bị vô hiệu hoá."""
        phong = await _them_phong_ban(db_session, "Phong Email 3")
        await _them_user(db_session, "nghiviec@congty.vn", "STAFF", phong, is_active=False)

        with pytest.raises(IntegrityError):
            await _them_user(db_session, "nghiviec@congty.vn", "STAFF", phong)


class TestRangBuocMotManagerMoiPhong:
    async def test_hai_manager_dang_hoat_dong_cung_phong_bi_tu_choi(
        self, db_session: AsyncSession
    ) -> None:
        """Đây là ràng buộc quan trọng nhất — chỉ cơ sở dữ liệu mới chặn được
        khi hai request xảy ra đồng thời."""
        phong = await _them_phong_ban(db_session, "Phong Manager 1")
        await _them_user(db_session, "m1@congty.vn", "MANAGER", phong)

        with pytest.raises(IntegrityError):
            await _them_user(db_session, "m2@congty.vn", "MANAGER", phong)

    async def test_manager_da_vo_hieu_hoa_khong_chiem_cho(
        self, db_session: AsyncSession
    ) -> None:
        phong = await _them_phong_ban(db_session, "Phong Manager 2")
        await _them_user(db_session, "cu@congty.vn", "MANAGER", phong, is_active=False)

        ma_moi = await _them_user(db_session, "moi@congty.vn", "MANAGER", phong)

        assert ma_moi is not None

    async def test_nhieu_staff_cung_phong_van_duoc(
        self, db_session: AsyncSession
    ) -> None:
        phong = await _them_phong_ban(db_session, "Phong Staff")
        await _them_user(db_session, "s1@congty.vn", "STAFF", phong)

        ma = await _them_user(db_session, "s2@congty.vn", "STAFF", phong)

        assert ma is not None

    async def test_hai_manager_o_hai_phong_khac_nhau_van_duoc(
        self, db_session: AsyncSession
    ) -> None:
        phong_a = await _them_phong_ban(db_session, "Phong A")
        phong_b = await _them_phong_ban(db_session, "Phong B")
        await _them_user(db_session, "ma@congty.vn", "MANAGER", phong_a)

        ma = await _them_user(db_session, "mb@congty.vn", "MANAGER", phong_b)

        assert ma is not None


class TestRangBuocVaiTro:
    async def test_vai_tro_khong_hop_le_bi_tu_choi(
        self, db_session: AsyncSession
    ) -> None:
        phong = await _them_phong_ban(db_session, "Phong Vai Tro")

        with pytest.raises(IntegrityError):
            await _them_user(db_session, "sai@congty.vn", "SUPERUSER", phong)

    async def test_admin_luu_duoc_voi_phong_ban_rong(
        self, db_session: AsyncSession
    ) -> None:
        ma = await _them_user(db_session, "admin@congty.vn", "ADMIN", None)

        assert ma is not None


class TestRangBuocTenPhongBan:
    async def test_ten_phong_ban_trung_bi_tu_choi(
        self, db_session: AsyncSession
    ) -> None:
        await _them_phong_ban(db_session, "Trung Ten")

        with pytest.raises(IntegrityError):
            await _them_phong_ban(db_session, "Trung Ten")


class TestKieuDuLieuThoiGian:
    @pytest.mark.parametrize(
        ("ten_bang", "ten_cot"),
        [
            ("users", "created_at"),
            ("users", "last_login_at"),
            ("departments", "created_at"),
            ("refresh_tokens", "expires_at"),
            ("audit_logs", "created_at"),
        ],
    )
    async def test_cot_thoi_gian_co_kem_mui_gio(
        self, db_session: AsyncSession, ten_bang: str, ten_cot: str
    ) -> None:
        ket_qua = await db_session.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = :bang AND column_name = :cot"
            ),
            {"bang": ten_bang, "cot": ten_cot},
        )

        assert ket_qua.scalar_one() == "timestamp with time zone"


class TestXoaTheoQuanHe:
    async def test_xoa_user_thi_refresh_token_cung_bi_xoa(
        self, db_session: AsyncSession
    ) -> None:
        phong = await _them_phong_ban(db_session, "Phong Cascade")
        user_id = await _them_user(db_session, "cascade@congty.vn", "STAFF", phong)
        await db_session.execute(
            text(
                "INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, "
                "revoked_at, replaced_by_id, user_agent, ip_address, created_at) "
                "VALUES (gen_random_uuid(), :uid, 'h', :het_han, NULL, NULL, NULL, NULL, :bg)"
            ),
            {"uid": user_id, "het_han": BAY_GIO + timedelta(days=7), "bg": BAY_GIO},
        )

        await db_session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})

        con_lai = await db_session.execute(
            text("SELECT count(*) FROM refresh_tokens WHERE user_id = :uid"),
            {"uid": user_id},
        )
        assert con_lai.scalar_one() == 0

    async def test_xoa_user_khong_lam_mat_nhat_ky(
        self, db_session: AsyncSession
    ) -> None:
        """Nhật ký phải sống sót — đó là mục đích tồn tại của nó."""
        phong = await _them_phong_ban(db_session, "Phong Audit")
        user_id = await _them_user(db_session, "audit@congty.vn", "STAFF", phong)
        await db_session.execute(
            text(
                "INSERT INTO audit_logs (id, actor_id, action, resource_type, "
                "resource_id, changes, ip_address, user_agent, created_at) "
                "VALUES (gen_random_uuid(), :uid, 'user.created', 'user', :uid, "
                "NULL, NULL, NULL, :bg)"
            ),
            {"uid": user_id, "bg": BAY_GIO},
        )

        await db_session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})

        con_lai = await db_session.execute(
            text("SELECT actor_id FROM audit_logs WHERE resource_id = :uid"),
            {"uid": user_id},
        )
        assert con_lai.scalar_one() is None
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/integration/test_schema.py -v
```

Expected: FAIL — các bảng chưa tồn tại.

- [ ] **Step 3: Viết `department_model.py`**

```python
"""ORM model cho bảng phòng ban."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class DepartmentModel(Base):
    """Bảng ``departments``.

    Chỉ mô tả cấu trúc bảng — mọi quy tắc nghiệp vụ nằm ở
    ``domain.entities.department.Department``.
    """

    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("uq_department_name", func.lower(name), unique=True),
        Index("ix_department_is_active", "is_active"),
    )
```

- [ ] **Step 4: Viết `user_model.py`**

```python
"""ORM model cho bảng người dùng."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class UserModel(Base):
    """Bảng ``users`` — chứa cả ba vai trò Staff, Manager và Admin."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # Email duy nhất vĩnh viễn, kể cả với tài khoản đã vô hiệu hoá.
        Index("uq_user_email", func.lower(email), unique=True),
        # Mỗi phòng ban tối đa một quản lý đang hoạt động. Ràng buộc này phải
        # nằm ở cơ sở dữ liệu: kiểm tra ở tầng ứng dụng không chặn được hai
        # request xảy ra đồng thời.
        Index(
            "uq_department_active_manager",
            "department_id",
            unique=True,
            postgresql_where=text("role = 'MANAGER' AND is_active"),
        ),
        CheckConstraint(
            "role IN ('STAFF', 'MANAGER', 'ADMIN')", name="ck_user_role_hop_le"
        ),
        # Staff và Manager bắt buộc thuộc phòng ban; Admin bắt buộc không.
        CheckConstraint(
            "(role = 'ADMIN' AND department_id IS NULL) "
            "OR (role IN ('STAFF', 'MANAGER') AND department_id IS NOT NULL)",
            name="ck_user_phong_ban_khop_vai_tro",
        ),
        Index("ix_user_department_id", "department_id"),
        Index("ix_user_is_active", "is_active"),
    )
```

- [ ] **Step 5: Viết `refresh_token_model.py`**

```python
"""ORM model cho bảng refresh token."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class RefreshTokenModel(Base):
    """Bảng ``refresh_tokens``.

    Xoá người dùng thì token bị xoá theo — token không còn ý nghĩa nếu chủ
    của nó không tồn tại.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_refresh_token_user_id", "user_id"),
        Index("ix_refresh_token_expires_at", "expires_at"),
    )
```

**Lưu ý:** `replaced_by_id` cố ý **không** khai báo khoá ngoại trỏ tới chính bảng này. Lý do: khi xoay token, bản ghi mới được tạo sau bản ghi cũ được cập nhật, nên khoá ngoại sẽ gây lỗi thứ tự trong cùng một giao dịch.

- [ ] **Step 6: Viết `audit_log_model.py`**

```python
"""ORM model cho bảng nhật ký kiểm toán."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class AuditLogModel(Base):
    """Bảng ``audit_logs`` — chỉ ghi thêm.

    ``actor_id`` dùng ``ON DELETE SET NULL`` chứ không cascade: xoá người dùng
    không được phép làm mất lịch sử hành động của họ.
    """

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    actor_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_log_created_at", created_at.desc()),
        Index("ix_audit_log_actor_id", "actor_id"),
        Index("ix_audit_log_action", "action"),
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
    )
```

- [ ] **Step 7: Cho Alembic thấy các model**

Sửa `backend/migrations/env.py`, thêm ngay sau dòng `from src.shared.infrastructure.database import Base`:

```python
# Import để Base.metadata biết tới các bảng. Không import thì autogenerate
# sẽ sinh ra migration rỗng.
from src.modules.identity.infrastructure.models.audit_log_model import AuditLogModel  # noqa: F401,E402
from src.modules.identity.infrastructure.models.department_model import (  # noqa: F401,E402
    DepartmentModel,
)
from src.modules.identity.infrastructure.models.refresh_token_model import (  # noqa: F401,E402
    RefreshTokenModel,
)
from src.modules.identity.infrastructure.models.user_model import UserModel  # noqa: F401,E402
```

- [ ] **Step 8: Tạo các file `__init__.py`**

```bash
cd backend
mkdir -p src/modules/identity/infrastructure/models
touch src/modules/identity/infrastructure/__init__.py \
      src/modules/identity/infrastructure/models/__init__.py
```

- [ ] **Step 9: Sinh migration**

```bash
uv run alembic revision --autogenerate -m "tao bang identity"
```

Expected: in ra `Generating .../migrations/versions/<hash>_tao_bang_identity.py ... done`.

- [ ] **Step 10: Đọc lại migration vừa sinh**

Mở file trong `migrations/versions/`. Kiểm tra:
- Có `op.create_table` cho cả bốn bảng.
- Có `op.create_index` cho `uq_user_email`, `uq_department_active_manager`, `uq_department_name`.
- Có `sa.CheckConstraint` cho `ck_user_role_hop_le` và `ck_user_phong_ban_khop_vai_tro`.

Nếu thiếu index partial `uq_department_active_manager`, thêm thủ công vào hàm `upgrade()`:

```python
    op.create_index(
        "uq_department_active_manager",
        "users",
        ["department_id"],
        unique=True,
        postgresql_where=sa.text("role = 'MANAGER' AND is_active"),
    )
```

và vào `downgrade()`:

```python
    op.drop_index("uq_department_active_manager", table_name="users")
```

- [ ] **Step 11: Bật extension sinh UUID**

Test dùng `gen_random_uuid()`. Hàm này có sẵn từ PostgreSQL 13 nên không cần extension. Xác nhận:

```bash
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -d omnichat -c "SELECT gen_random_uuid();"
```

Expected: in ra một UUID.

- [ ] **Step 12: Áp migration lên cả hai cơ sở dữ liệu**

```bash
cd backend
uv run alembic upgrade head
```

Áp cho cơ sở dữ liệu test bằng cách trỏ tạm `DATABASE_URL` sang nó:

```bash
DATABASE_URL="postgresql+psycopg://postgres@localhost:5432/omnichat_test" uv run alembic upgrade head
```

Expected: `Running upgrade -> <hash>, tao bang identity`.

- [ ] **Step 13: Chạy test schema**

```bash
uv run pytest tests/integration/test_schema.py -v
```

Expected: `18 passed`.

- [ ] **Step 14: Kiểm tra migration đảo ngược được**

```bash
DATABASE_URL="postgresql+psycopg://postgres@localhost:5432/omnichat_test" uv run alembic downgrade base
DATABASE_URL="postgresql+psycopg://postgres@localhost:5432/omnichat_test" uv run alembic upgrade head
```

Expected: cả hai lệnh chạy không lỗi. Migration không đảo ngược được là migration chưa hoàn chỉnh.

- [ ] **Step 15: Commit**

```bash
git add backend/src/modules/identity/infrastructure backend/migrations \
        backend/tests/integration/test_schema.py
git commit -m "feat: add identity orm models and initial migration"
```

---

## Task 10: Mapper hai chiều

**Files:**
- Create: `backend/src/modules/identity/infrastructure/mappers/__init__.py`
- Create: `backend/src/modules/identity/infrastructure/mappers/department_mapper.py`
- Create: `backend/src/modules/identity/infrastructure/mappers/user_mapper.py`
- Create: `backend/src/modules/identity/infrastructure/mappers/refresh_token_mapper.py`
- Create: `backend/src/modules/identity/infrastructure/mappers/audit_log_mapper.py`
- Test: `backend/tests/unit/identity/test_mappers.py`

**Interfaces:**
- Consumes: entity từ Task 5–7, ORM model từ Task 9.
- Produces:
  - `DepartmentMapper.to_domain(model: DepartmentModel) -> Department` và `.to_model(entity: Department) -> DepartmentModel`; `.update_model(model: DepartmentModel, entity: Department) -> None`.
  - `UserMapper.to_domain`, `.to_model`, `.update_model` — cùng dạng.
  - `RefreshTokenMapper.to_domain`, `.to_model`, `.update_model`.
  - `AuditLogMapper.to_model` — chỉ một chiều khi ghi, và `.to_domain` khi đọc.

**Ghi chú thiết kế:** `update_model` tồn tại vì khi cập nhật, bản ghi đã nằm trong session của SQLAlchemy. Tạo model mới sẽ khiến SQLAlchemy coi đó là bản ghi khác; phải sửa trực tiếp lên model đang được theo dõi.

- [ ] **Step 1: Viết test mapper**

File `backend/tests/unit/identity/test_mappers.py`:

```python
"""Mapper phải giữ nguyên dữ liệu qua cả hai chiều chuyển đổi."""

from datetime import UTC, datetime

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.mappers.audit_log_mapper import AuditLogMapper
from src.modules.identity.infrastructure.mappers.department_mapper import (
    DepartmentMapper,
)
from src.modules.identity.infrastructure.mappers.refresh_token_mapper import (
    RefreshTokenMapper,
)
from src.modules.identity.infrastructure.mappers.user_mapper import UserMapper
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
SAU_DO = datetime(2026, 7, 21, 11, 0, tzinfo=UTC)
PHONG_A = new_id()


class TestDepartmentMapper:
    def test_chuyen_hai_chieu_khong_mat_du_lieu(self) -> None:
        goc = Department.create(name="Kinh doanh", description="Mô tả", now=BAY_GIO)

        quay_lai = DepartmentMapper.to_domain(DepartmentMapper.to_model(goc))

        assert quay_lai.id == goc.id
        assert quay_lai.name == goc.name
        assert quay_lai.description == goc.description
        assert quay_lai.is_active == goc.is_active
        assert quay_lai.created_at == goc.created_at
        assert quay_lai.updated_at == goc.updated_at

    def test_update_model_ghi_de_len_model_dang_co(self) -> None:
        goc = Department.create(name="Cũ", description=None, now=BAY_GIO)
        model = DepartmentMapper.to_model(goc)
        goc.rename("Mới", now=SAU_DO)

        DepartmentMapper.update_model(model, goc)

        assert model.name == "Mới"
        assert model.updated_at == SAU_DO
        assert model.id == goc.id


class TestUserMapper:
    def _user(self, role: Role = Role.STAFF) -> User:
        return User.create(
            email=Email("nhanvien@congty.vn"),
            password_hash=PasswordHash("$2b$12$hash"),
            full_name="Nguyễn Văn A",
            role=role,
            department_id=PHONG_A if role.requires_department() else None,
            now=BAY_GIO,
            phone="0900000000",
        )

    def test_chuyen_hai_chieu_khong_mat_du_lieu(self) -> None:
        goc = self._user()

        quay_lai = UserMapper.to_domain(UserMapper.to_model(goc))

        assert quay_lai.id == goc.id
        assert quay_lai.email == goc.email
        assert quay_lai.password_hash == goc.password_hash
        assert quay_lai.full_name == goc.full_name
        assert quay_lai.phone == goc.phone
        assert quay_lai.role is goc.role
        assert quay_lai.department_id == goc.department_id
        assert quay_lai.is_active == goc.is_active
        assert quay_lai.must_change_password == goc.must_change_password
        assert quay_lai.last_login_at == goc.last_login_at

    def test_vai_tro_luu_thanh_chuoi_va_doc_lai_thanh_enum(self) -> None:
        model = UserMapper.to_model(self._user(Role.MANAGER))

        assert model.role == "MANAGER"
        assert isinstance(model.role, str)
        assert UserMapper.to_domain(model).role is Role.MANAGER

    def test_email_luu_duoi_dang_chuoi(self) -> None:
        model = UserMapper.to_model(self._user())

        assert model.email == "nhanvien@congty.vn"

    def test_admin_khong_co_phong_ban(self) -> None:
        model = UserMapper.to_model(self._user(Role.ADMIN))

        assert model.department_id is None
        assert UserMapper.to_domain(model).department_id is None

    def test_giu_nguyen_moc_dang_nhap_gan_nhat(self) -> None:
        goc = self._user()
        goc.record_login(now=SAU_DO)

        assert UserMapper.to_domain(UserMapper.to_model(goc)).last_login_at == SAU_DO


class TestRefreshTokenMapper:
    def test_chuyen_hai_chieu_khong_mat_du_lieu(self) -> None:
        goc = RefreshToken.issue(
            user_id=new_id(),
            token_hash="hash_gia_lap",
            expires_at=SAU_DO,
            now=BAY_GIO,
            user_agent="Chrome",
            ip_address="10.0.0.1",
        )

        quay_lai = RefreshTokenMapper.to_domain(RefreshTokenMapper.to_model(goc))

        assert quay_lai.id == goc.id
        assert quay_lai.user_id == goc.user_id
        assert quay_lai.token_hash == goc.token_hash
        assert quay_lai.expires_at == goc.expires_at
        assert quay_lai.user_agent == goc.user_agent
        assert quay_lai.ip_address == goc.ip_address

    def test_giu_nguyen_trang_thai_da_xoay(self) -> None:
        goc = RefreshToken.issue(new_id(), "h", SAU_DO, BAY_GIO)
        ma_moi = new_id()
        goc.rotate_to(ma_moi, now=SAU_DO)

        quay_lai = RefreshTokenMapper.to_domain(RefreshTokenMapper.to_model(goc))

        assert quay_lai.revoked_at == SAU_DO
        assert quay_lai.replaced_by_id == ma_moi
        assert quay_lai.is_revoked() is True


class TestAuditLogMapper:
    def test_chuyen_hai_chieu_khong_mat_du_lieu(self) -> None:
        goc = AuditLog.record(
            action=AuditAction.USER_ROLE_CHANGED,
            actor_id=new_id(),
            resource_type="user",
            resource_id="abc",
            now=BAY_GIO,
            changes={"role": {"truoc": "STAFF", "sau": "MANAGER"}},
            ip_address="10.0.0.1",
            user_agent="Chrome",
        )

        quay_lai = AuditLogMapper.to_domain(AuditLogMapper.to_model(goc))

        assert quay_lai.action is AuditAction.USER_ROLE_CHANGED
        assert quay_lai.actor_id == goc.actor_id
        assert quay_lai.resource_type == goc.resource_type
        assert quay_lai.resource_id == goc.resource_id
        assert quay_lai.changes == goc.changes
        assert quay_lai.created_at == goc.created_at

    def test_hanh_dong_luu_thanh_chuoi(self) -> None:
        goc = AuditLog.record(
            action=AuditAction.AUTH_LOGIN_FAILED,
            actor_id=None,
            resource_type="auth",
            resource_id=None,
            now=BAY_GIO,
        )

        assert AuditLogMapper.to_model(goc).action == "auth.login_failed"
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/unit/identity/test_mappers.py -v
```

Expected: FAIL với `ModuleNotFoundError` cho `mappers`.

- [ ] **Step 3: Viết `department_mapper.py`**

```python
"""Chuyển đổi giữa ORM model và domain entity của phòng ban."""

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.infrastructure.models.department_model import DepartmentModel


class DepartmentMapper:
    """Cầu nối giữa bảng ``departments`` và entity ``Department``."""

    @staticmethod
    def to_domain(model: DepartmentModel) -> Department:
        return Department(
            id=model.id,
            name=model.name,
            description=model.description,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: Department) -> DepartmentModel:
        return DepartmentModel(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def update_model(model: DepartmentModel, entity: Department) -> None:
        """Ghi thay đổi lên model đang được session theo dõi.

        Không tạo model mới: SQLAlchemy sẽ coi model mới là một bản ghi khác.
        """
        model.name = entity.name
        model.description = entity.description
        model.is_active = entity.is_active
        model.updated_at = entity.updated_at
```

- [ ] **Step 4: Viết `user_mapper.py`**

```python
"""Chuyển đổi giữa ORM model và domain entity của người dùng."""

from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.models.user_model import UserModel


class UserMapper:
    """Cầu nối giữa bảng ``users`` và entity ``User``.

    Value object được tháo ra thành chuỗi khi ghi và dựng lại khi đọc.
    """

    @staticmethod
    def to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            email=Email(model.email),
            password_hash=PasswordHash(model.password_hash),
            full_name=model.full_name,
            phone=model.phone,
            role=Role(model.role),
            department_id=model.department_id,
            is_active=model.is_active,
            must_change_password=model.must_change_password,
            last_login_at=model.last_login_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: User) -> UserModel:
        return UserModel(
            id=entity.id,
            email=entity.email.value,
            password_hash=entity.password_hash.value,
            full_name=entity.full_name,
            phone=entity.phone,
            role=entity.role.value,
            department_id=entity.department_id,
            is_active=entity.is_active,
            must_change_password=entity.must_change_password,
            last_login_at=entity.last_login_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def update_model(model: UserModel, entity: User) -> None:
        model.email = entity.email.value
        model.password_hash = entity.password_hash.value
        model.full_name = entity.full_name
        model.phone = entity.phone
        model.role = entity.role.value
        model.department_id = entity.department_id
        model.is_active = entity.is_active
        model.must_change_password = entity.must_change_password
        model.last_login_at = entity.last_login_at
        model.updated_at = entity.updated_at
```

- [ ] **Step 5: Viết `refresh_token_mapper.py`**

```python
"""Chuyển đổi giữa ORM model và domain entity của refresh token."""

from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.infrastructure.models.refresh_token_model import (
    RefreshTokenModel,
)


class RefreshTokenMapper:
    """Cầu nối giữa bảng ``refresh_tokens`` và entity ``RefreshToken``."""

    @staticmethod
    def to_domain(model: RefreshTokenModel) -> RefreshToken:
        return RefreshToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
            replaced_by_id=model.replaced_by_id,
            user_agent=model.user_agent,
            ip_address=model.ip_address,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: RefreshToken) -> RefreshTokenModel:
        return RefreshTokenModel(
            id=entity.id,
            user_id=entity.user_id,
            token_hash=entity.token_hash,
            expires_at=entity.expires_at,
            revoked_at=entity.revoked_at,
            replaced_by_id=entity.replaced_by_id,
            user_agent=entity.user_agent,
            ip_address=entity.ip_address,
            created_at=entity.created_at,
        )

    @staticmethod
    def update_model(model: RefreshTokenModel, entity: RefreshToken) -> None:
        model.revoked_at = entity.revoked_at
        model.replaced_by_id = entity.replaced_by_id
```

- [ ] **Step 6: Viết `audit_log_mapper.py`**

```python
"""Chuyển đổi giữa ORM model và domain entity của nhật ký kiểm toán."""

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.infrastructure.models.audit_log_model import AuditLogModel


class AuditLogMapper:
    """Cầu nối giữa bảng ``audit_logs`` và entity ``AuditLog``.

    Không có ``update_model``: nhật ký chỉ được ghi thêm.
    """

    @staticmethod
    def to_domain(model: AuditLogModel) -> AuditLog:
        return AuditLog(
            id=model.id,
            action=AuditAction(model.action),
            actor_id=model.actor_id,
            resource_type=model.resource_type,
            resource_id=model.resource_id,
            changes=model.changes,
            ip_address=model.ip_address,
            user_agent=model.user_agent,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: AuditLog) -> AuditLogModel:
        return AuditLogModel(
            id=entity.id,
            action=entity.action.value,
            actor_id=entity.actor_id,
            resource_type=entity.resource_type,
            resource_id=entity.resource_id,
            changes=entity.changes,
            ip_address=entity.ip_address,
            user_agent=entity.user_agent,
            created_at=entity.created_at,
        )
```

- [ ] **Step 7: Chạy test để xác nhận thành công**

```bash
cd backend
mkdir -p src/modules/identity/infrastructure/mappers
touch src/modules/identity/infrastructure/mappers/__init__.py
uv run pytest tests/unit/identity/test_mappers.py -v
```

Expected: `12 passed`.

- [ ] **Step 8: Kiểm tra chất lượng mã**

```bash
uv run mypy src
uv run ruff check .
uv run lint-imports
```

Expected: xanh.

- [ ] **Step 9: Commit**

```bash
git add backend/src/modules/identity/infrastructure/mappers \
        backend/tests/unit/identity/test_mappers.py
git commit -m "feat: add bidirectional mappers between orm models and entities"
```

---

## Task 11: Repository implementation

**Files:**
- Create: `backend/src/modules/identity/infrastructure/repositories/__init__.py`
- Create: `backend/src/modules/identity/infrastructure/repositories/user_repository.py`
- Create: `backend/src/modules/identity/infrastructure/repositories/department_repository.py`
- Create: `backend/src/modules/identity/infrastructure/repositories/refresh_token_repository.py`
- Create: `backend/src/modules/identity/infrastructure/repositories/audit_log_repository.py`
- Test: `backend/tests/integration/test_user_repository.py`
- Test: `backend/tests/integration/test_department_repository.py`
- Test: `backend/tests/integration/test_refresh_token_repository.py`

**Interfaces:**
- Consumes: interface từ Task 8, mapper từ Task 10.
- Produces:
  - `SqlAlchemyUserRepository(session: AsyncSession)` — implement `IUserRepository`.
  - `SqlAlchemyDepartmentRepository(session: AsyncSession)` — implement `IDepartmentRepository`.
  - `SqlAlchemyRefreshTokenRepository(session: AsyncSession)` — implement `IRefreshTokenRepository`.
  - `SqlAlchemyAuditLogRepository(session: AsyncSession)` — implement `IAuditLogRepository`.

- [ ] **Step 1: Viết test cho `SqlAlchemyUserRepository`**

File `backend/tests/integration/test_user_repository.py`:

```python
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


async def _tao_phong(session: AsyncSession, ten: str) -> Department:
    phong = Department.create(name=ten, description=None, now=BAY_GIO)
    await SqlAlchemyDepartmentRepository(session).add(phong)
    await session.flush()
    return phong


def _user(
    email: str, role: Role, department_id, full_name: str = "Nguyễn Văn A"
) -> User:
    return User.create(
        email=Email(email),
        password_hash=PasswordHash("$2b$12$hash"),
        full_name=full_name,
        role=role,
        department_id=department_id,
        now=BAY_GIO,
    )


class TestLuuVaDoc:
    async def test_luu_roi_doc_lai_duoc_theo_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng 1")
        goc = _user("a@congty.vn", Role.STAFF, phong.id)

        await repo.add(goc)
        await db_session.flush()
        doc_lai = await repo.get_by_id(goc.id)

        assert doc_lai is not None
        assert doc_lai.id == goc.id
        assert doc_lai.email == goc.email
        assert doc_lai.role is Role.STAFF

    async def test_tim_theo_email_khong_phan_biet_hoa_thuong(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng 2")
        await repo.add(_user("hoathuong@congty.vn", Role.STAFF, phong.id))
        await db_session.flush()

        assert await repo.get_by_email(Email("HoaThuong@CongTy.VN")) is not None

    async def test_khong_tim_thay_thi_tra_ve_none(
        self, db_session: AsyncSession
    ) -> None:
        from src.shared.domain.identifiers import new_id

        repo = SqlAlchemyUserRepository(db_session)

        assert await repo.get_by_id(new_id()) is None
        assert await repo.get_by_email(Email("khongton@tai.vn")) is None

    async def test_cap_nhat_duoc_luu_lai(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng 3")
        user = _user("capnhat@congty.vn", Role.STAFF, phong.id)
        await repo.add(user)
        await db_session.flush()

        user.update_profile(full_name="Tên Mới", phone="0911111111", now=BAY_GIO)
        await repo.update(user)
        await db_session.flush()

        doc_lai = await repo.get_by_id(user.id)
        assert doc_lai is not None
        assert doc_lai.full_name == "Tên Mới"
        assert doc_lai.phone == "0911111111"


class TestDemVaKiemTra:
    async def test_dem_nhan_vien_dang_hoat_dong_trong_phong(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Đếm")
        dang_lam = _user("a@congty.vn", Role.STAFF, phong.id)
        nghi_viec = _user("b@congty.vn", Role.STAFF, phong.id)
        nghi_viec.deactivate(is_last_active_admin=False, now=BAY_GIO)
        await repo.add(dang_lam)
        await repo.add(nghi_viec)
        await db_session.flush()

        assert await repo.count_active_in_department(phong.id) == 1

    async def test_phat_hien_phong_da_co_quan_ly(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Quản Lý")
        manager = _user("m@congty.vn", Role.MANAGER, phong.id)
        await repo.add(manager)
        await db_session.flush()

        assert await repo.has_active_manager(phong.id) is True
        assert await repo.has_active_manager(phong.id, exclude_user_id=manager.id) is False

    async def test_quan_ly_da_vo_hieu_hoa_khong_tinh_la_dang_hoat_dong(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Quản Lý Cũ")
        manager = _user("mcu@congty.vn", Role.MANAGER, phong.id)
        manager.deactivate(is_last_active_admin=False, now=BAY_GIO)
        await repo.add(manager)
        await db_session.flush()

        assert await repo.has_active_manager(phong.id) is False

    async def test_dem_quan_tri_vien_dang_hoat_dong(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        truoc = await repo.count_active_admins()
        await repo.add(_user("ad@congty.vn", Role.ADMIN, None))
        await db_session.flush()

        assert await repo.count_active_admins() == truoc + 1


class TestLocVaPhanTrang:
    async def test_loc_theo_phong_ban(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong_a = await _tao_phong(db_session, "Phòng Lọc A")
        phong_b = await _tao_phong(db_session, "Phòng Lọc B")
        await repo.add(_user("a@congty.vn", Role.STAFF, phong_a.id))
        await repo.add(_user("b@congty.vn", Role.STAFF, phong_b.id))
        await db_session.flush()

        ket_qua = await repo.list_users(department_id=phong_a.id)

        assert len(ket_qua) == 1
        assert ket_qua[0].email == Email("a@congty.vn")

    async def test_loc_theo_vai_tro(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Vai Trò")
        await repo.add(_user("s@congty.vn", Role.STAFF, phong.id))
        await repo.add(_user("m@congty.vn", Role.MANAGER, phong.id))
        await db_session.flush()

        ket_qua = await repo.list_users(department_id=phong.id, role=Role.MANAGER)

        assert len(ket_qua) == 1
        assert ket_qua[0].role is Role.MANAGER

    async def test_tim_kiem_khop_ho_ten_khong_phan_biet_hoa_thuong(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Tìm Kiếm")
        await repo.add(
            _user("timkiem@congty.vn", Role.STAFF, phong.id, full_name="Trần Thị Bích")
        )
        await db_session.flush()

        assert len(await repo.list_users(department_id=phong.id, search="trần")) == 1
        assert len(await repo.list_users(department_id=phong.id, search="TIMKIEM")) == 1
        assert len(await repo.list_users(department_id=phong.id, search="xyz")) == 0

    async def test_phan_trang_tra_ve_dung_so_luong(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Phân Trang")
        for i in range(5):
            await repo.add(_user(f"pt{i}@congty.vn", Role.STAFF, phong.id))
        await db_session.flush()

        trang_dau = await repo.list_users(department_id=phong.id, limit=2, offset=0)
        trang_hai = await repo.list_users(department_id=phong.id, limit=2, offset=2)

        assert len(trang_dau) == 2
        assert len(trang_hai) == 2
        assert {u.id for u in trang_dau} & {u.id for u in trang_hai} == set()

    async def test_dem_khop_voi_bo_loc_cua_danh_sach(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        phong = await _tao_phong(db_session, "Phòng Đếm Lọc")
        for i in range(3):
            await repo.add(_user(f"dl{i}@congty.vn", Role.STAFF, phong.id))
        await db_session.flush()

        assert await repo.count_users(department_id=phong.id) == 3
```

- [ ] **Step 2: Viết test cho repository phòng ban và refresh token**

File `backend/tests/integration/test_department_repository.py`:

```python
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


async def test_luu_roi_doc_lai_duoc(db_session: AsyncSession) -> None:
    repo = SqlAlchemyDepartmentRepository(db_session)
    goc = Department.create(name="Kinh doanh", description="Mô tả", now=BAY_GIO)

    await repo.add(goc)
    await db_session.flush()

    doc_lai = await repo.get_by_id(goc.id)
    assert doc_lai is not None
    assert doc_lai.name == "Kinh doanh"
    assert doc_lai.description == "Mô tả"


async def test_tim_theo_ten_khong_phan_biet_hoa_thuong(
    db_session: AsyncSession,
) -> None:
    repo = SqlAlchemyDepartmentRepository(db_session)
    await repo.add(Department.create(name="Chăm Sóc", description=None, now=BAY_GIO))
    await db_session.flush()

    assert await repo.get_by_name("chăm sóc") is not None


async def test_khong_tim_thay_phong_ban_da_vo_hieu_hoa(
    db_session: AsyncSession,
) -> None:
    repo = SqlAlchemyDepartmentRepository(db_session)
    phong = Department.create(name="Đã Đóng", description=None, now=BAY_GIO)
    phong.deactivate(active_member_count=0, now=BAY_GIO)
    await repo.add(phong)
    await db_session.flush()

    assert await repo.get_by_name("Đã Đóng") is None


async def test_loc_theo_trang_thai_hoat_dong(db_session: AsyncSession) -> None:
    repo = SqlAlchemyDepartmentRepository(db_session)
    dang_mo = Department.create(name="Đang Mở", description=None, now=BAY_GIO)
    da_dong = Department.create(name="Đóng Rồi", description=None, now=BAY_GIO)
    da_dong.deactivate(active_member_count=0, now=BAY_GIO)
    await repo.add(dang_mo)
    await repo.add(da_dong)
    await db_session.flush()

    dang_hoat_dong = await repo.list_departments(is_active=True)

    assert dang_mo.id in {d.id for d in dang_hoat_dong}
    assert da_dong.id not in {d.id for d in dang_hoat_dong}


async def test_cap_nhat_duoc_luu_lai(db_session: AsyncSession) -> None:
    repo = SqlAlchemyDepartmentRepository(db_session)
    phong = Department.create(name="Tên Cũ", description=None, now=BAY_GIO)
    await repo.add(phong)
    await db_session.flush()

    phong.rename("Tên Mới", now=BAY_GIO)
    await repo.update(phong)
    await db_session.flush()

    doc_lai = await repo.get_by_id(phong.id)
    assert doc_lai is not None
    assert doc_lai.name == "Tên Mới"
```

File `backend/tests/integration/test_refresh_token_repository.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)
HET_HAN = BAY_GIO + timedelta(days=7)


async def _tao_user(db_session: AsyncSession, email: str) -> User:
    phong = Department.create(name=f"Phòng {email}", description=None, now=BAY_GIO)
    await SqlAlchemyDepartmentRepository(db_session).add(phong)
    await db_session.flush()
    user = User.create(
        email=Email(email),
        password_hash=PasswordHash("$2b$12$hash"),
        full_name="Người dùng",
        role=Role.STAFF,
        department_id=phong.id,
        now=BAY_GIO,
    )
    await SqlAlchemyUserRepository(db_session).add(user)
    await db_session.flush()
    return user


async def test_tim_duoc_token_theo_hash(db_session: AsyncSession) -> None:
    user = await _tao_user(db_session, "token1@congty.vn")
    repo = SqlAlchemyRefreshTokenRepository(db_session)
    token = RefreshToken.issue(user.id, "hash_duy_nhat_1", HET_HAN, BAY_GIO)

    await repo.add(token)
    await db_session.flush()

    doc_lai = await repo.get_by_hash("hash_duy_nhat_1")
    assert doc_lai is not None
    assert doc_lai.user_id == user.id


async def test_thu_hoi_moi_token_cua_mot_nguoi_dung(
    db_session: AsyncSession,
) -> None:
    user = await _tao_user(db_session, "token2@congty.vn")
    repo = SqlAlchemyRefreshTokenRepository(db_session)
    for i in range(3):
        await repo.add(RefreshToken.issue(user.id, f"hash_thu_hoi_{i}", HET_HAN, BAY_GIO))
    await db_session.flush()

    await repo.revoke_all_for_user(user.id, now=BAY_GIO + timedelta(hours=1))
    await db_session.flush()

    for i in range(3):
        token = await repo.get_by_hash(f"hash_thu_hoi_{i}")
        assert token is not None
        assert token.is_revoked() is True


async def test_thu_hoi_toan_bo_chuoi_token(db_session: AsyncSession) -> None:
    """Khi phát hiện token bị tái sử dụng, cả chuỗi phải mất hiệu lực."""
    user = await _tao_user(db_session, "token3@congty.vn")
    repo = SqlAlchemyRefreshTokenRepository(db_session)
    dau = RefreshToken.issue(user.id, "chuoi_dau", HET_HAN, BAY_GIO)
    giua = RefreshToken.issue(user.id, "chuoi_giua", HET_HAN, BAY_GIO)
    cuoi = RefreshToken.issue(user.id, "chuoi_cuoi", HET_HAN, BAY_GIO)
    dau.rotate_to(giua.id, BAY_GIO)
    giua.rotate_to(cuoi.id, BAY_GIO)
    for t in (dau, giua, cuoi):
        await repo.add(t)
    await db_session.flush()

    await repo.revoke_chain(dau, now=BAY_GIO + timedelta(hours=1))
    await db_session.flush()

    ban_cuoi = await repo.get_by_hash("chuoi_cuoi")
    assert ban_cuoi is not None
    assert ban_cuoi.is_revoked() is True
```

- [ ] **Step 3: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/integration/test_user_repository.py -v
```

Expected: FAIL với `ModuleNotFoundError` cho `repositories`.

- [ ] **Step 4: Viết `user_repository.py`**

```python
"""Repository người dùng dùng SQLAlchemy."""

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.mappers.user_mapper import UserMapper
from src.modules.identity.infrastructure.models.user_model import UserModel


class SqlAlchemyUserRepository:
    """Truy xuất người dùng từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lay_model(self, user_id: UUID) -> UserModel | None:
        ket_qua = await self._session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return ket_qua.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._lay_model(user_id)
        return UserMapper.to_domain(model) if model else None

    async def get_by_email(self, email: Email) -> User | None:
        ket_qua = await self._session.execute(
            select(UserModel).where(func.lower(UserModel.email) == email.value)
        )
        model = ket_qua.scalar_one_or_none()
        return UserMapper.to_domain(model) if model else None

    async def add(self, user: User) -> None:
        self._session.add(UserMapper.to_model(user))

    async def update(self, user: User) -> None:
        """Ghi thay đổi lên bản ghi đang có.

        Phải đọc model ra trước rồi sửa, thay vì tạo model mới — nếu không
        SQLAlchemy sẽ coi đó là một bản ghi khác và cố chèn thêm.
        """
        model = await self._lay_model(user.id)
        if model is None:
            raise ValueError(f"Không tìm thấy người dùng {user.id} để cập nhật.")
        UserMapper.update_model(model, user)

    def _ap_dung_bo_loc(
        self,
        cau_truy_van: Select[tuple[UserModel]],
        department_id: UUID | None,
        role: Role | None,
        is_active: bool | None,
        search: str | None,
    ) -> Select[tuple[UserModel]]:
        if department_id is not None:
            cau_truy_van = cau_truy_van.where(UserModel.department_id == department_id)
        if role is not None:
            cau_truy_van = cau_truy_van.where(UserModel.role == role.value)
        if is_active is not None:
            cau_truy_van = cau_truy_van.where(UserModel.is_active == is_active)
        if search:
            mau = f"%{search.lower()}%"
            cau_truy_van = cau_truy_van.where(
                func.lower(UserModel.full_name).like(mau)
                | func.lower(UserModel.email).like(mau)
            )
        return cau_truy_van

    async def list_users(
        self,
        department_id: UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        cau_truy_van = self._ap_dung_bo_loc(
            select(UserModel), department_id, role, is_active, search
        )
        cau_truy_van = cau_truy_van.order_by(UserModel.created_at).limit(limit).offset(offset)
        ket_qua = await self._session.execute(cau_truy_van)
        return [UserMapper.to_domain(m) for m in ket_qua.scalars()]

    async def count_users(
        self,
        department_id: UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> int:
        cau_truy_van = self._ap_dung_bo_loc(
            select(func.count()).select_from(UserModel),  # type: ignore[arg-type]
            department_id,
            role,
            is_active,
            search,
        )
        ket_qua = await self._session.execute(cau_truy_van)
        return int(ket_qua.scalar_one())

    async def count_active_in_department(self, department_id: UUID) -> int:
        ket_qua = await self._session.execute(
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.department_id == department_id, UserModel.is_active)
        )
        return int(ket_qua.scalar_one())

    async def has_active_manager(
        self, department_id: UUID, exclude_user_id: UUID | None = None
    ) -> bool:
        cau_truy_van = (
            select(func.count())
            .select_from(UserModel)
            .where(
                UserModel.department_id == department_id,
                UserModel.role == Role.MANAGER.value,
                UserModel.is_active,
            )
        )
        if exclude_user_id is not None:
            cau_truy_van = cau_truy_van.where(UserModel.id != exclude_user_id)
        ket_qua = await self._session.execute(cau_truy_van)
        return int(ket_qua.scalar_one()) > 0

    async def count_active_admins(self) -> int:
        ket_qua = await self._session.execute(
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.role == Role.ADMIN.value, UserModel.is_active)
        )
        return int(ket_qua.scalar_one())
```

- [ ] **Step 5: Viết `department_repository.py`**

```python
"""Repository phòng ban dùng SQLAlchemy."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.infrastructure.mappers.department_mapper import (
    DepartmentMapper,
)
from src.modules.identity.infrastructure.models.department_model import DepartmentModel


class SqlAlchemyDepartmentRepository:
    """Truy xuất phòng ban từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lay_model(self, department_id: UUID) -> DepartmentModel | None:
        ket_qua = await self._session.execute(
            select(DepartmentModel).where(DepartmentModel.id == department_id)
        )
        return ket_qua.scalar_one_or_none()

    async def get_by_id(self, department_id: UUID) -> Department | None:
        model = await self._lay_model(department_id)
        return DepartmentMapper.to_domain(model) if model else None

    async def get_by_name(self, name: str) -> Department | None:
        """Tìm trong các phòng ban đang hoạt động, không phân biệt hoa thường."""
        ket_qua = await self._session.execute(
            select(DepartmentModel).where(
                func.lower(DepartmentModel.name) == name.strip().lower(),
                DepartmentModel.is_active,
            )
        )
        model = ket_qua.scalar_one_or_none()
        return DepartmentMapper.to_domain(model) if model else None

    async def add(self, department: Department) -> None:
        self._session.add(DepartmentMapper.to_model(department))

    async def update(self, department: Department) -> None:
        model = await self._lay_model(department.id)
        if model is None:
            raise ValueError(f"Không tìm thấy phòng ban {department.id} để cập nhật.")
        DepartmentMapper.update_model(model, department)

    async def list_departments(
        self,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Department]:
        cau_truy_van = select(DepartmentModel)
        if is_active is not None:
            cau_truy_van = cau_truy_van.where(DepartmentModel.is_active == is_active)
        cau_truy_van = cau_truy_van.order_by(DepartmentModel.name).limit(limit).offset(offset)
        ket_qua = await self._session.execute(cau_truy_van)
        return [DepartmentMapper.to_domain(m) for m in ket_qua.scalars()]

    async def count_departments(self, is_active: bool | None = None) -> int:
        cau_truy_van = select(func.count()).select_from(DepartmentModel)
        if is_active is not None:
            cau_truy_van = cau_truy_van.where(DepartmentModel.is_active == is_active)
        ket_qua = await self._session.execute(cau_truy_van)
        return int(ket_qua.scalar_one())
```

- [ ] **Step 6: Viết `refresh_token_repository.py`**

```python
"""Repository refresh token dùng SQLAlchemy."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.infrastructure.mappers.refresh_token_mapper import (
    RefreshTokenMapper,
)
from src.modules.identity.infrastructure.models.refresh_token_model import (
    RefreshTokenModel,
)


class SqlAlchemyRefreshTokenRepository:
    """Truy xuất refresh token từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        ket_qua = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        model = ket_qua.scalar_one_or_none()
        return RefreshTokenMapper.to_domain(model) if model else None

    async def add(self, token: RefreshToken) -> None:
        self._session.add(RefreshTokenMapper.to_model(token))

    async def update(self, token: RefreshToken) -> None:
        ket_qua = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.id == token.id)
        )
        model = ket_qua.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Không tìm thấy refresh token {token.id} để cập nhật.")
        RefreshTokenMapper.update_model(model, token)

    async def revoke_all_for_user(self, user_id: UUID, now: datetime) -> None:
        """Thu hồi mọi token chưa bị thu hồi của người dùng bằng một câu lệnh."""
        await self._session.execute(
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

    async def revoke_chain(self, token: RefreshToken, now: datetime) -> None:
        """Thu hồi toàn bộ chuỗi token nối tiếp nhau.

        Duyệt theo ``replaced_by_id``. Có tập ``da_duyet`` để dừng nếu dữ liệu
        bị hỏng tạo thành vòng lặp.
        """
        ma_hien_tai: UUID | None = token.id
        da_duyet: set[UUID] = set()

        while ma_hien_tai is not None and ma_hien_tai not in da_duyet:
            da_duyet.add(ma_hien_tai)
            ket_qua = await self._session.execute(
                select(RefreshTokenModel).where(RefreshTokenModel.id == ma_hien_tai)
            )
            model = ket_qua.scalar_one_or_none()
            if model is None:
                break
            if model.revoked_at is None:
                model.revoked_at = now
            ma_hien_tai = model.replaced_by_id
```

- [ ] **Step 7: Viết `audit_log_repository.py`**

```python
"""Repository nhật ký kiểm toán dùng SQLAlchemy."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.infrastructure.mappers.audit_log_mapper import AuditLogMapper
from src.modules.identity.infrastructure.models.audit_log_model import AuditLogModel


class SqlAlchemyAuditLogRepository:
    """Ghi và tra cứu nhật ký kiểm toán trong PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: AuditLog) -> None:
        self._session.add(AuditLogMapper.to_model(entry))

    def _ap_dung_bo_loc(
        self,
        cau_truy_van: Select[tuple[AuditLogModel]],
        actor_id: UUID | None,
        action: AuditAction | None,
        resource_type: str | None,
        from_time: datetime | None,
        to_time: datetime | None,
    ) -> Select[tuple[AuditLogModel]]:
        if actor_id is not None:
            cau_truy_van = cau_truy_van.where(AuditLogModel.actor_id == actor_id)
        if action is not None:
            cau_truy_van = cau_truy_van.where(AuditLogModel.action == action.value)
        if resource_type is not None:
            cau_truy_van = cau_truy_van.where(
                AuditLogModel.resource_type == resource_type
            )
        if from_time is not None:
            cau_truy_van = cau_truy_van.where(AuditLogModel.created_at >= from_time)
        if to_time is not None:
            cau_truy_van = cau_truy_van.where(AuditLogModel.created_at <= to_time)
        return cau_truy_van

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
        cau_truy_van = self._ap_dung_bo_loc(
            select(AuditLogModel), actor_id, action, resource_type, from_time, to_time
        )
        cau_truy_van = (
            cau_truy_van.order_by(AuditLogModel.created_at.desc()).limit(limit).offset(offset)
        )
        ket_qua = await self._session.execute(cau_truy_van)
        return [AuditLogMapper.to_domain(m) for m in ket_qua.scalars()]

    async def count_entries(
        self,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        resource_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> int:
        cau_truy_van = self._ap_dung_bo_loc(
            select(func.count()).select_from(AuditLogModel),  # type: ignore[arg-type]
            actor_id,
            action,
            resource_type,
            from_time,
            to_time,
        )
        ket_qua = await self._session.execute(cau_truy_van)
        return int(ket_qua.scalar_one())
```

- [ ] **Step 8: Chạy test integration**

```bash
cd backend
mkdir -p src/modules/identity/infrastructure/repositories
touch src/modules/identity/infrastructure/repositories/__init__.py
uv run pytest tests/integration -v
```

Expected: toàn bộ xanh, `40 passed`.

- [ ] **Step 9: Kiểm tra chất lượng mã**

```bash
uv run mypy src
uv run ruff check .
uv run lint-imports
```

Expected: xanh.

- [ ] **Step 10: Commit**

```bash
git add backend/src/modules/identity/infrastructure/repositories backend/tests/integration
git commit -m "feat: add sqlalchemy repository implementations"
```

---

## Task 12: Băm mật khẩu và cấp phát JWT

**Files:**
- Create: `backend/src/modules/identity/application/__init__.py`
- Create: `backend/src/modules/identity/application/ports.py`
- Create: `backend/src/modules/identity/infrastructure/security/__init__.py`
- Create: `backend/src/modules/identity/infrastructure/security/password_hasher.py`
- Create: `backend/src/modules/identity/infrastructure/security/token_service.py`
- Test: `backend/tests/unit/identity/test_security.py`

**Interfaces:**
- Consumes: `Settings` từ Task 3, `Role` từ Task 4.
- Produces:
  - `IPasswordHasher` — protocol: `hash(plain_password: str) -> str`; `verify(plain_password: str, hashed: str) -> bool`.
  - `ITokenService` — protocol: `create_access_token(user_id: UUID, role: Role, department_id: UUID | None) -> str`; `decode_access_token(token: str) -> AccessTokenPayload`; `create_refresh_token() -> tuple[str, str]` trả về `(token_thô, hash)`; `hash_refresh_token(token: str) -> str`.
  - `AccessTokenPayload` — frozen dataclass: `user_id: UUID`, `role: Role`, `department_id: UUID | None`, `expires_at: datetime`.
  - `InvalidTokenError`, `ExpiredTokenError` — kế thừa `ApplicationError`.
  - `BcryptPasswordHasher(rounds: int = 12)`.
  - `JwtTokenService(secret_key, algorithm, access_token_expire_minutes, clock)`.

- [ ] **Step 1: Viết test bảo mật**

File `backend/tests/unit/identity/test_security.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest

from src.modules.identity.application.ports import (
    ExpiredTokenError,
    InvalidTokenError,
)
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.security.password_hasher import (
    BcryptPasswordHasher,
)
from src.modules.identity.infrastructure.security.token_service import JwtTokenService
from src.shared.domain.identifiers import new_id
from tests.unit.identity.fakes import FakeClock

KHOA_BI_MAT = "khoa-bi-mat-chi-dung-cho-test-khong-dung-that"
BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


class TestBamMatKhau:
    def test_bam_roi_kiem_tra_lai_dung(self) -> None:
        hasher = BcryptPasswordHasher()
        chuoi_hash = hasher.hash("MatKhauCuaToi123")

        assert hasher.verify("MatKhauCuaToi123", chuoi_hash) is True

    def test_mat_khau_sai_bi_tu_choi(self) -> None:
        hasher = BcryptPasswordHasher()
        chuoi_hash = hasher.hash("MatKhauDung123")

        assert hasher.verify("MatKhauSai123", chuoi_hash) is False

    def test_hai_lan_bam_cung_mat_khau_cho_hai_hash_khac_nhau(self) -> None:
        """Bcrypt tự sinh salt ngẫu nhiên, nên hash khác nhau là đúng."""
        hasher = BcryptPasswordHasher()

        assert hasher.hash("GiongNhau123") != hasher.hash("GiongNhau123")

    def test_hash_khong_chua_mat_khau_goc(self) -> None:
        hasher = BcryptPasswordHasher()

        assert "MatKhauLoRa" not in hasher.hash("MatKhauLoRa")

    def test_hash_sai_dinh_dang_thi_tra_ve_false_chu_khong_no(self) -> None:
        """Chuỗi hash hỏng trong cơ sở dữ liệu không được làm sập đăng nhập."""
        hasher = BcryptPasswordHasher()

        assert hasher.verify("bat_ky", "khong-phai-hash-bcrypt") is False

    def test_mat_khau_dai_hon_72_byte_van_bam_duoc(self) -> None:
        """Bcrypt ném ValueError với đầu vào quá 72 byte nếu không rút gọn trước."""
        hasher = BcryptPasswordHasher()
        rat_dai = "a" * 200

        assert hasher.verify(rat_dai, hasher.hash(rat_dai)) is True

    def test_mat_khau_tieng_viet_co_dau_bam_duoc(self) -> None:
        """Ký tự tiếng Việt chiếm nhiều byte — 140 ký tự có thể thành 195 byte."""
        hasher = BcryptPasswordHasher()
        tieng_viet = "Mật khẩu tiếng Việt rất dài " * 5

        assert hasher.verify(tieng_viet, hasher.hash(tieng_viet)) is True

    def test_hai_mat_khau_dai_khac_nhau_khong_bi_coi_la_giong_nhau(self) -> None:
        """Nếu cắt thô ở 72 byte, hai mật khẩu này sẽ trùng nhau — lỗ hổng thật."""
        hasher = BcryptPasswordHasher()
        chung = "x" * 80
        chuoi_hash = hasher.hash(chung + "phan_duoi_A")

        assert hasher.verify(chung + "phan_duoi_B", chuoi_hash) is False


class TestAccessToken:
    def _dich_vu(self, clock: FakeClock | None = None) -> JwtTokenService:
        return JwtTokenService(
            secret_key=KHOA_BI_MAT,
            algorithm="HS256",
            access_token_expire_minutes=15,
            clock=clock or FakeClock(BAY_GIO),
        )

    def test_tao_roi_giai_ma_lay_lai_dung_thong_tin(self) -> None:
        dich_vu = self._dich_vu()
        user_id = new_id()
        phong_id = new_id()

        token = dich_vu.create_access_token(user_id, Role.MANAGER, phong_id)
        payload = dich_vu.decode_access_token(token)

        assert payload.user_id == user_id
        assert payload.role is Role.MANAGER
        assert payload.department_id == phong_id

    def test_admin_khong_co_phong_ban_trong_token(self) -> None:
        dich_vu = self._dich_vu()

        token = dich_vu.create_access_token(new_id(), Role.ADMIN, None)

        assert dich_vu.decode_access_token(token).department_id is None

    def test_token_het_han_bi_tu_choi(self) -> None:
        dong_ho = FakeClock(BAY_GIO)
        dich_vu = self._dich_vu(dong_ho)
        token = dich_vu.create_access_token(new_id(), Role.STAFF, new_id())

        dong_ho.advance(minutes=16)

        with pytest.raises(ExpiredTokenError):
            dich_vu.decode_access_token(token)

    def test_token_con_han_thi_chap_nhan(self) -> None:
        dong_ho = FakeClock(BAY_GIO)
        dich_vu = self._dich_vu(dong_ho)
        token = dich_vu.create_access_token(new_id(), Role.STAFF, new_id())

        dong_ho.advance(minutes=14)

        assert dich_vu.decode_access_token(token) is not None

    def test_token_bi_sua_doi_bi_tu_choi(self) -> None:
        dich_vu = self._dich_vu()
        token = dich_vu.create_access_token(new_id(), Role.STAFF, new_id())

        bi_sua = token[:-4] + "xxxx"

        with pytest.raises(InvalidTokenError):
            dich_vu.decode_access_token(bi_sua)

    def test_token_ky_bang_khoa_khac_bi_tu_choi(self) -> None:
        """Đây là điều ngăn kẻ tấn công tự cấp token cho mình."""
        ke_tan_cong = JwtTokenService(
            secret_key="khoa-khac-hoan-toan",
            algorithm="HS256",
            access_token_expire_minutes=15,
            clock=FakeClock(BAY_GIO),
        )
        token_gia = ke_tan_cong.create_access_token(new_id(), Role.ADMIN, None)

        with pytest.raises(InvalidTokenError):
            self._dich_vu().decode_access_token(token_gia)

    @pytest.mark.parametrize("rac", ["", "khong-phai-jwt", "a.b.c", "..."])
    def test_chuoi_rac_bi_tu_choi(self, rac: str) -> None:
        with pytest.raises(InvalidTokenError):
            self._dich_vu().decode_access_token(rac)

    def test_thoi_diem_het_han_dung_bang_15_phut(self) -> None:
        dich_vu = self._dich_vu()

        token = dich_vu.create_access_token(new_id(), Role.STAFF, new_id())

        payload = dich_vu.decode_access_token(token)
        assert payload.expires_at == BAY_GIO + timedelta(minutes=15)


class TestRefreshToken:
    def _dich_vu(self) -> JwtTokenService:
        return JwtTokenService(
            secret_key=KHOA_BI_MAT,
            algorithm="HS256",
            access_token_expire_minutes=15,
            clock=FakeClock(BAY_GIO),
        )

    def test_moi_lan_tao_cho_mot_token_khac_nhau(self) -> None:
        dich_vu = self._dich_vu()

        tho_1, _ = dich_vu.create_refresh_token()
        tho_2, _ = dich_vu.create_refresh_token()

        assert tho_1 != tho_2

    def test_hash_tra_ve_khop_voi_ham_bam(self) -> None:
        dich_vu = self._dich_vu()

        tho, chuoi_hash = dich_vu.create_refresh_token()

        assert dich_vu.hash_refresh_token(tho) == chuoi_hash

    def test_hash_khong_chua_token_goc(self) -> None:
        """Cơ sở dữ liệu chỉ lưu hash — đọc được bảng cũng không mạo danh được."""
        dich_vu = self._dich_vu()

        tho, chuoi_hash = dich_vu.create_refresh_token()

        assert tho not in chuoi_hash

    def test_bam_cung_mot_token_luon_cho_cung_ket_qua(self) -> None:
        dich_vu = self._dich_vu()
        tho, _ = dich_vu.create_refresh_token()

        assert dich_vu.hash_refresh_token(tho) == dich_vu.hash_refresh_token(tho)

    def test_token_du_dai_de_khong_the_doan(self) -> None:
        tho, _ = self._dich_vu().create_refresh_token()

        assert len(tho) >= 32
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/unit/identity/test_security.py -v
```

Expected: FAIL với `ModuleNotFoundError`.

- [ ] **Step 3: Viết `application/ports.py`**

```python
"""Port bảo mật mà tầng application cần."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.exceptions import ApplicationError


class InvalidTokenError(ApplicationError):
    """Token sai định dạng, sai chữ ký, hoặc thiếu trường bắt buộc."""

    def __init__(self) -> None:
        super().__init__("Token không hợp lệ.", code="INVALID_TOKEN")


class ExpiredTokenError(ApplicationError):
    """Token đã quá hạn sử dụng."""

    def __init__(self) -> None:
        super().__init__("Token đã hết hạn.", code="EXPIRED_TOKEN")


@dataclass(frozen=True)
class AccessTokenPayload:
    """Thông tin lấy được từ một access token hợp lệ."""

    user_id: UUID
    role: Role
    department_id: UUID | None
    expires_at: datetime


class IPasswordHasher(Protocol):
    """Băm và kiểm tra mật khẩu."""

    def hash(self, plain_password: str) -> str: ...

    def verify(self, plain_password: str, hashed: str) -> bool:
        """Trả về ``False`` khi sai mật khẩu hoặc khi chuỗi hash hỏng.

        Không được ném ngoại lệ: chuỗi hash hỏng trong cơ sở dữ liệu phải dẫn
        tới đăng nhập thất bại, không phải lỗi 500.
        """
        ...


class ITokenService(Protocol):
    """Cấp phát và kiểm tra token."""

    def create_access_token(
        self, user_id: UUID, role: Role, department_id: UUID | None
    ) -> str: ...

    def decode_access_token(self, token: str) -> AccessTokenPayload:
        """Giải mã và kiểm tra token.

        Ném ``ExpiredTokenError`` nếu hết hạn, ``InvalidTokenError`` nếu chữ ký
        sai hoặc nội dung không đúng cấu trúc.
        """
        ...

    def create_refresh_token(self) -> tuple[str, str]:
        """Sinh refresh token mới.

        Trả về ``(token_thô, hash)``. Token thô gửi cho client, hash lưu vào
        cơ sở dữ liệu.
        """
        ...

    def hash_refresh_token(self, token: str) -> str:
        """Băm token thô để đối chiếu với giá trị đã lưu."""
        ...
```

- [ ] **Step 4: Viết `password_hasher.py`**

```python
"""Băm mật khẩu bằng bcrypt."""

import base64
import hashlib

import bcrypt


class BcryptPasswordHasher:
    """Băm mật khẩu bằng bcrypt.

    Bcrypt tự sinh salt cho mỗi lần băm, nên hai người dùng đặt cùng mật khẩu
    vẫn có hash khác nhau.

    Mật khẩu được rút gọn bằng SHA-256 trước khi đưa vào bcrypt — xem
    ``_rut_gon`` để biết lý do.
    """

    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    @staticmethod
    def _rut_gon(plain_password: str) -> bytes:
        """Rút gọn mật khẩu về 44 byte cố định bằng SHA-256 rồi base64.

        Bcrypt chỉ nhận tối đa 72 byte và từ phiên bản 4.1 trở đi nó **ném
        ``ValueError``** thay vì lặng lẽ cắt bớt. Cắt thủ công ở byte 72 cũng
        không ổn: mật khẩu tiếng Việt có dấu dùng nhiều byte cho mỗi ký tự
        (140 ký tự có thể thành 195 byte), nên cắt thô dễ rơi vào giữa một ký
        tự UTF-8 và tạo ra chuỗi byte hỏng.

        Băm SHA-256 trước cho ra độ dài cố định, giữ được toàn bộ entropy của
        mật khẩu gốc dù dài bao nhiêu. Base64 để tránh ký tự NUL — bcrypt cắt
        chuỗi tại byte NUL đầu tiên.
        """
        tom_tat = hashlib.sha256(plain_password.encode("utf-8")).digest()
        return base64.b64encode(tom_tat)

    def hash(self, plain_password: str) -> str:
        muoi = bcrypt.gensalt(rounds=self._rounds)
        return bcrypt.hashpw(self._rut_gon(plain_password), muoi).decode("utf-8")

    def verify(self, plain_password: str, hashed: str) -> bool:
        """So khớp mật khẩu với chuỗi hash.

        Chuỗi hash hỏng trả về ``False`` thay vì ném ngoại lệ, để dữ liệu lỗi
        trong cơ sở dữ liệu không làm sập luồng đăng nhập.
        """
        try:
            return bcrypt.checkpw(
                self._rut_gon(plain_password), hashed.encode("utf-8")
            )
        except (ValueError, TypeError):
            return False
```

- [ ] **Step 5: Viết `token_service.py`**

```python
"""Cấp phát và kiểm tra JWT."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from src.modules.identity.application.ports import (
    AccessTokenPayload,
    ExpiredTokenError,
    InvalidTokenError,
)
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.ports import IClock


class JwtTokenService:
    """Cấp access token dạng JWT và refresh token dạng chuỗi ngẫu nhiên.

    Access token là JWT tự chứa thông tin, không cần tra cứu cơ sở dữ liệu khi
    kiểm tra. Refresh token ngược lại chỉ là chuỗi ngẫu nhiên, phải đối chiếu
    với bản ghi trong cơ sở dữ liệu — nhờ đó thu hồi được.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        access_token_expire_minutes: int,
        clock: IClock,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self._clock = clock

    def create_access_token(
        self, user_id: UUID, role: Role, department_id: UUID | None
    ) -> str:
        bay_gio = self._clock.now()
        het_han = bay_gio + self._access_token_expire
        noi_dung = {
            "sub": str(user_id),
            "role": role.value,
            "dept": str(department_id) if department_id else None,
            "iat": int(bay_gio.timestamp()),
            "exp": int(het_han.timestamp()),
        }
        return jwt.encode(noi_dung, self._secret_key, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> AccessTokenPayload:
        """Giải mã token và tự kiểm tra hạn theo ``IClock``.

        ``verify_exp`` được tắt có chủ đích: PyJWT so ``exp`` với đồng hồ hệ
        thống thật, bỏ qua ``IClock``. Nếu để PyJWT tự kiểm tra thì test không
        điều khiển được thời gian, và mọi test dùng mốc thời gian cố định sẽ
        cho kết quả phụ thuộc vào lúc chạy. Chữ ký vẫn được PyJWT xác minh —
        phần bị tắt chỉ là so sánh thời gian, và nó được làm lại ngay bên dưới.
        """
        try:
            noi_dung = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"require": ["sub", "exp", "iat"], "verify_exp": False},
            )
        except jwt.PyJWTError as loi:
            raise InvalidTokenError from loi

        try:
            ma_phong = noi_dung["dept"]
            het_han = datetime.fromtimestamp(noi_dung["exp"], tz=UTC)
            payload = AccessTokenPayload(
                user_id=UUID(noi_dung["sub"]),
                role=Role(noi_dung["role"]),
                department_id=UUID(ma_phong) if ma_phong else None,
                expires_at=het_han,
            )
        except (KeyError, ValueError) as loi:
            raise InvalidTokenError from loi

        if self._clock.now() >= het_han:
            raise ExpiredTokenError
        return payload

    def create_refresh_token(self) -> tuple[str, str]:
        """Sinh refresh token 43 ký tự từ nguồn ngẫu nhiên an toàn mật mã."""
        tho = secrets.token_urlsafe(32)
        return tho, self.hash_refresh_token(tho)

    def hash_refresh_token(self, token: str) -> str:
        """Băm bằng SHA-256.

        Không dùng bcrypt ở đây: refresh token đã là chuỗi ngẫu nhiên 256 bit
        nên không sợ tấn công từ điển, và SHA-256 cho phép tra cứu trực tiếp
        theo hash trong cơ sở dữ liệu.
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
```

**Vì sao phải tự kiểm tra hạn thay vì để PyJWT làm.** Nếu bật `verify_exp` mặc định, PyJWT so `exp` với `datetime.now()` của hệ thống. Khi đó `JwtTokenService` có hai nguồn thời gian mâu thuẫn: `IClock` lúc tạo token, đồng hồ thật lúc kiểm tra. Hệ quả trong test là mọi mốc thời gian cố định đều hỏng — một token tạo tại `FakeClock(2026-07-21 10:00)` sẽ bị coi là hết hạn ngay lập tức nếu lúc chạy test đã quá 10:15 giờ thật, khiến `test_token_con_han_thi_chap_nhan` đỏ và `test_token_het_han_bi_tu_choi` xanh vì lý do sai.

Tắt `verify_exp` rồi so sánh bằng `self._clock.now()` khiến toàn bộ vòng đời token đi qua đúng một nguồn thời gian. Chữ ký vẫn do PyJWT xác minh đầy đủ.

- [ ] **Step 6: Chạy test để xác nhận thành công**

```bash
cd backend
mkdir -p src/modules/identity/infrastructure/security
touch src/modules/identity/application/__init__.py \
      src/modules/identity/infrastructure/security/__init__.py
uv run pytest tests/unit/identity/test_security.py -v
```

Expected: `23 passed`.

Toàn bộ nhóm test này dùng mốc thời gian cố định `BAY_GIO` và phải xanh bất kể chạy vào lúc nào — đó chính là điều mà việc tự kiểm tra hạn ở Step 5 bảo đảm.

- [ ] **Step 7: Chạy toàn bộ test**

```bash
uv run pytest -v
```

Expected: toàn bộ xanh.

- [ ] **Step 8: Kiểm tra chất lượng mã**

```bash
uv run mypy src
uv run ruff check .
uv run lint-imports
```

Expected: `Contracts: 3 kept, 0 broken.`

- [ ] **Step 9: Commit**

```bash
git add backend/src/modules/identity/application backend/src/modules/identity/infrastructure/security \
        backend/tests/unit/identity/test_security.py
git commit -m "feat: add bcrypt password hashing and jwt token service"
```

---

## Tiếp theo

- [Phần 4 — Use case và API](2026-07-21-omnichat-foundation-part4-api.md) (Task 13–20)
