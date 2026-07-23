# OmniChat Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây nền tảng kỹ thuật cho OmniChat — clean architecture, PostgreSQL, xác thực JWT, phân quyền ba vai trò, và quản lý người dùng/phòng ban.

**Architecture:** Clean Architecture tổ chức theo module dọc. Mỗi module có bốn layer `domain / application / infrastructure / presentation`, tuân thủ dependency rule một chiều hướng vào `domain`. Domain entity là dataclass thuần Python, tách khỏi SQLAlchemy model qua mapper. Toàn bộ tầng I/O chạy async.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0 (async) · psycopg 3 · PostgreSQL 17 · Alembic · Pydantic v2 · uv · pytest · ruff · mypy · import-linter

**Spec:** [2026-07-21-omnichat-foundation-design.md](../specs/2026-07-21-omnichat-foundation-design.md)

## Global Constraints

- Python 3.13 — môi trường thực tế là 3.13.9.
- PostgreSQL 17 cài native trên Windows tại `C:\Program Files\PostgreSQL\17`. **Không dùng Docker** — máy phát triển không có Docker.
- Database dev: `omnichat`. Database test: `omnichat_test`. User: `postgres`, host `localhost`, cổng `5432`.
- `src/modules/*/domain/` chỉ được import stdlib. Cấm import SQLAlchemy, FastAPI, Pydantic. Ràng buộc này do `import-linter` kiểm tra trong CI.
- Mọi truy cập cơ sở dữ liệu dùng `AsyncSession`; mọi use case là `async def`.
- **Trên Windows phải chuyển event loop sang `WindowsSelectorEventLoopPolicy` trước khi mở kết nối async.** psycopg từ chối chạy trên `ProactorEventLoop` — event loop mặc định của Windows — với `InterfaceError: Psycopg cannot use the 'ProactorEventLoop' to run in async mode`. Mọi entry point chạy code async (`tests/conftest.py`, `migrations/env.py`, `src/main.py`, và các script trong `scripts/`) phải gọi `cau_hinh_event_loop()` từ `src/shared/infrastructure/event_loop.py` trước khi tạo engine. Hàm này không làm gì trên Linux và macOS.
- Khoá chính là UUID v7 sinh ở tầng ứng dụng qua hàm `new_id()` trong `src/shared/domain/identifiers.py`. **Thư viện chuẩn Python 3.13 không có `uuid.uuid7()`** — hàm đó chỉ xuất hiện từ Python 3.14. Dự án dùng gói `uuid-utils` và bọc lại sau một hàm duy nhất, để khi nâng lên Python 3.14 chỉ phải sửa một chỗ.
- Mọi cột thời gian dùng `TIMESTAMP WITH TIME ZONE`, lưu UTC.
- `role` lưu VARCHAR kèm CHECK constraint, không dùng kiểu ENUM của PostgreSQL.
- Access token sống 15 phút, refresh token sống 7 ngày.
- Mật khẩu băm bằng bcrypt cost 12. Refresh token lưu dưới dạng SHA-256 hash.
- Tên test viết tiếng Việt không dấu, mô tả hành vi: `test_khong_cho_phep_hai_manager_trong_cung_phong_ban`.
- Coverage mục tiêu: `domain` và `application` ≥ 90%, tổng thể ≥ 80%.
- Mọi lệnh chạy trong thư mục `backend/`, qua `uv run`.

## Bản đồ file

| Đường dẫn | Trách nhiệm |
|---|---|
| `src/shared/domain/identifiers.py` | `new_id()` — sinh UUID v7 |
| `src/shared/domain/entity.py` | Lớp cơ sở `Entity`, `AggregateRoot` |
| `src/shared/domain/value_object.py` | Lớp cơ sở `ValueObject` |
| `src/shared/domain/exceptions.py` | `DomainError`, `BusinessRuleViolationError` |
| `src/shared/application/exceptions.py` | `NotFoundError`, `PermissionDeniedError`, `AuthenticationError`, `ConflictError` |
| `src/shared/application/unit_of_work.py` | Interface `IUnitOfWork` |
| `src/shared/application/ports.py` | Port `IClock` |
| `src/shared/infrastructure/config.py` | `Settings` đọc từ biến môi trường |
| `src/shared/infrastructure/database.py` | Async engine, session factory, `Base` |
| `src/shared/infrastructure/sqlalchemy_uow.py` | `SqlAlchemyUnitOfWork` |
| `src/shared/infrastructure/clock.py` | `SystemClock` |
| `src/shared/infrastructure/event_loop.py` | `cau_hinh_event_loop()` — chọn event loop tương thích psycopg trên Windows |
| `src/shared/infrastructure/logging.py` | Structured logging kèm `request_id` |
| `src/modules/identity/domain/value_objects/` | `Email`, `PasswordHash`, `Role` |
| `src/modules/identity/domain/entities/` | `User`, `Department`, `RefreshToken`, `AuditLog` |
| `src/modules/identity/domain/repositories/` | Interface repository |
| `src/modules/identity/application/ports.py` | `IPasswordHasher`, `ITokenService` |
| `src/modules/identity/application/use_cases/` | Một file một use case |
| `src/modules/identity/infrastructure/models/` | SQLAlchemy ORM model |
| `src/modules/identity/infrastructure/mappers/` | Chuyển đổi ORM model ↔ domain entity |
| `src/modules/identity/infrastructure/repositories/` | Repository implementation |
| `src/modules/identity/infrastructure/security/` | `BcryptPasswordHasher`, `JwtTokenService` |
| `src/modules/identity/presentation/routers/` | FastAPI router |
| `src/modules/identity/presentation/schemas/` | Pydantic request/response |
| `src/modules/identity/presentation/dependencies.py` | DI wiring, `get_current_user`, `require_role` |
| `src/main.py` | Composition root, exception handler, middleware |

## Danh sách Task

Plan chia làm bốn file để mỗi task giữ đủ chi tiết. Thực hiện tuần tự.

### Giai đoạn 1 — Nền tảng kỹ thuật (file này)

| Task | Nội dung | Deliverable kiểm chứng được |
|---|---|---|
| 1 | Khởi tạo project, uv, cấu hình chất lượng mã | `uv run pytest` chạy được, `ruff`/`mypy`/`import-linter` xanh |
| 2 | Shared kernel: entity, value object, exception, clock | Unit test cho lớp cơ sở xanh |
| 3 | Kết nối cơ sở dữ liệu, Alembic, Unit of Work | Integration test kết nối DB thật xanh |

### Giai đoạn 2 — Domain Identity

Xem [phần 2](2026-07-21-omnichat-foundation-part2-domain.md).

| Task | Nội dung |
|---|---|
| 4 | Value object `Email`, `Role`, `PasswordHash` |
| 5 | Entity `Department` kèm business rule |
| 6 | Entity `User` kèm toàn bộ business rule |
| 7 | Entity `RefreshToken` và `AuditLog` |
| 8 | Interface repository |

### Giai đoạn 3 — Hạ tầng lưu trữ

Xem [phần 3](2026-07-21-omnichat-foundation-part3-infra.md).

| Task | Nội dung |
|---|---|
| 9 | ORM model và migration đầu tiên |
| 10 | Mapper hai chiều |
| 11 | Repository implementation |
| 12 | Bcrypt hasher và JWT token service |

### Giai đoạn 4 — Use case và API

Xem [phần 4](2026-07-21-omnichat-foundation-part4-api.md).

| Task | Nội dung |
|---|---|
| 13 | Use case xác thực |
| 14 | Use case quản lý người dùng |
| 15 | Use case quản lý phòng ban và audit log |
| 16 | FastAPI app, dependency, exception handler |
| 17 | Router xác thực |
| 18 | Router người dùng và phòng ban |
| 19 | Rate limit, health check, seed script |
| 20 | E2E test và CI pipeline |

---

## Task 1: Khởi tạo project và công cụ chất lượng mã

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.python-version`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/README.md`
- Create: `backend/src/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/unit/__init__.py`
- Create: `backend/tests/unit/test_smoke.py`

**Interfaces:**
- Consumes: không có — đây là task đầu tiên.
- Produces: cấu trúc project chạy được bằng `uv run pytest`; các lệnh `uv run ruff check .`, `uv run mypy src`, `uv run lint-imports` dùng được ở mọi task sau.

- [ ] **Step 1: Cài uv**

`uv` chưa có trên máy. Chạy trong PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Mở terminal mới rồi kiểm tra:

```bash
uv --version
```

Expected: in ra phiên bản, ví dụ `uv 0.9.x`.

- [ ] **Step 2: Tạo `backend/.python-version`**

```
3.13
```

- [ ] **Step 3: Tạo `backend/pyproject.toml`**

```toml
[project]
name = "omnichat-backend"
version = "0.1.0"
description = "OmniChat — hệ thống tập trung tin nhắn đa kênh"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlalchemy[asyncio]>=2.0.36",
    "psycopg[binary,pool]>=3.2",
    "alembic>=1.14",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "pyjwt>=2.10",
    "bcrypt>=4.2",
    "python-json-logger>=3.2",
    "uuid-utils>=0.10",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.25",
    "pytest-cov>=6.0",
    "httpx>=0.28",
    "ruff>=0.9",
    "mypy>=1.14",
    "import-linter>=2.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --strict-markers"
markers = [
    "integration: test cần cơ sở dữ liệu thật",
    "e2e: test đi qua toàn bộ API",
]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "C4", "SIM", "RUF"]

[tool.ruff.lint.per-file-ignores]
# File migration do Alembic autogenerate — không áp style thủ công lên chúng.
# Sửa tay theo ruff sẽ khiến lần autogenerate sau lại sinh khác và gây nhiễu diff.
"migrations/*" = ["E501", "I001", "UP007", "UP035"]

[tool.mypy]
python_version = "3.13"
strict = true
files = ["src"]

[[tool.mypy.overrides]]
module = "tests.*"
ignore_errors = true

[tool.coverage.run]
source = ["src"]
omit = [
    "src/main.py",
    # Interface repository và port chỉ là Protocol với thân ``...`` — không có
    # logic để test và không bao giờ được khởi tạo, nên đo coverage chúng vô
    # nghĩa và kéo tụt con số một cách giả tạo.
    "src/modules/*/domain/repositories/*.py",
    "src/modules/*/application/ports.py",
]

[tool.importlinter]
root_package = "src"
# Bắt buộc khi contract cấm import gói ngoài (sqlalchemy, fastapi, pydantic).
# Thiếu dòng này, import-linter báo lỗi cấu hình thay vì kiểm tra contract.
include_external_packages = true

[[tool.importlinter.contracts]]
name = "Domain khong duoc phu thuoc tang ngoai"
type = "forbidden"
source_modules = ["src.shared.domain", "src.modules.identity.domain"]
forbidden_modules = [
    "src.shared.infrastructure",
    "src.modules.identity.infrastructure",
    "src.modules.identity.presentation",
    "sqlalchemy",
    "fastapi",
    "pydantic",
]

[[tool.importlinter.contracts]]
name = "Application khong duoc phu thuoc infrastructure va presentation"
type = "forbidden"
source_modules = ["src.shared.application", "src.modules.identity.application"]
forbidden_modules = [
    "src.shared.infrastructure",
    "src.modules.identity.infrastructure",
    "src.modules.identity.presentation",
    "sqlalchemy",
    "fastapi",
]

[[tool.importlinter.contracts]]
name = "Cac layer tuan thu thu tu mot chieu"
type = "layers"
layers = [
    "src.modules.identity.presentation",
    "src.modules.identity.infrastructure",
    "src.modules.identity.application",
    "src.modules.identity.domain",
]
```

**Lưu ý về `pyjwt`:** spec ghi HS256. Dùng `pyjwt` chứ không dùng `python-jose` của code cũ — `python-jose` đã ngừng bảo trì và có lịch sử lỗ hổng bảo mật.

- [ ] **Step 4: Tạo `backend/.env.example`**

```dotenv
# Cơ sở dữ liệu — PostgreSQL 17 cài native trên Windows
DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/omnichat
TEST_DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/omnichat_test

# JWT — sinh khoá bằng: python -c "import secrets; print(secrets.token_urlsafe(64))"
JWT_SECRET_KEY=thay-bang-khoa-that-truoc-khi-chay
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate limit cho endpoint dang nhap
LOGIN_RATE_LIMIT_ATTEMPTS=5
LOGIN_RATE_LIMIT_WINDOW_SECONDS=300

# Ung dung
APP_ENV=development
LOG_LEVEL=INFO
```

- [ ] **Step 5: Tạo `backend/.gitignore`**

```gitignore
__pycache__/
*.py[cod]
.venv/
.env
.pytest_cache/
.mypy_cache/
.ruff_cache/
.import_linter_cache/
.coverage
htmlcov/
*.egg-info/
dist/
build/
```

- [ ] **Step 6: Tạo các file `__init__.py` rỗng**

```bash
mkdir -p backend/src backend/tests/unit
touch backend/src/__init__.py backend/tests/__init__.py backend/tests/unit/__init__.py
```

- [ ] **Step 7: Viết test smoke**

File `backend/tests/unit/test_smoke.py`:

```python
def test_moi_truong_test_chay_duoc() -> None:
    assert True
```

- [ ] **Step 8: Cài dependency và chạy test**

```bash
cd backend
uv sync
uv run pytest tests/unit/test_smoke.py -v
```

Expected: `1 passed`.

- [ ] **Step 9: Chạy các công cụ chất lượng mã**

```bash
uv run ruff check .
uv run ruff format --check .
```

Expected: `All checks passed!`. Nếu `ruff format --check` báo lỗi định dạng, chạy `uv run ruff format .` rồi chạy lại.

- [ ] **Step 10: Tạo `backend/README.md`**

````markdown
# OmniChat Backend

Nền tảng backend cho hệ thống tập trung tin nhắn đa kênh OmniChat.

## Yêu cầu môi trường

- Python 3.13
- PostgreSQL 17 (cài native, không dùng Docker)
- uv

## Cài đặt

```bash
cd backend
uv sync
cp .env.example .env
```

Sửa `.env`, đặt `JWT_SECRET_KEY` bằng khoá thật:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Tạo cơ sở dữ liệu

```bash
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -c "CREATE DATABASE omnichat;"
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -c "CREATE DATABASE omnichat_test;"
```

## Chạy test

```bash
uv run pytest tests/unit -v                 # nhanh, không cần cơ sở dữ liệu
uv run pytest tests/integration -v          # cần PostgreSQL
uv run pytest -v                            # toàn bộ
```

## Kiểm tra chất lượng mã

```bash
uv run ruff check .
uv run mypy src
uv run lint-imports
```
````

- [ ] **Step 11: Commit**

```bash
git add backend/pyproject.toml backend/.python-version backend/.env.example \
        backend/.gitignore backend/README.md backend/uv.lock \
        backend/src/__init__.py backend/tests/__init__.py \
        backend/tests/unit/__init__.py backend/tests/unit/test_smoke.py
git commit -m "chore: scaffold backend project with uv and quality tooling"
```

---

## Task 2: Shared kernel

**Files:**
- Create: `backend/src/shared/__init__.py`
- Create: `backend/src/shared/domain/__init__.py`
- Create: `backend/src/shared/domain/identifiers.py`
- Create: `backend/src/shared/domain/entity.py`
- Create: `backend/src/shared/domain/value_object.py`
- Create: `backend/src/shared/domain/exceptions.py`
- Create: `backend/src/shared/application/__init__.py`
- Create: `backend/src/shared/application/exceptions.py`
- Create: `backend/src/shared/application/ports.py`
- Create: `backend/src/shared/infrastructure/__init__.py`
- Create: `backend/src/shared/infrastructure/clock.py`
- Test: `backend/tests/unit/shared/test_entity.py`
- Test: `backend/tests/unit/shared/test_exceptions.py`
- Test: `backend/tests/unit/shared/test_identifiers.py`
- Test: `backend/tests/unit/shared/test_clock.py`

**Interfaces:**
- Consumes: cấu trúc project từ Task 1.
- Produces:
  - `new_id() -> UUID` — sinh UUID v7, sắp xếp được theo thời gian. Mọi entity dùng hàm này làm giá trị mặc định cho `id`.
  - `Entity` — dataclass base, có `id: UUID`, so sánh theo `id`.
  - `ValueObject` — base cho frozen dataclass.
  - `DomainError(message: str, code: str)` — lớp gốc mọi lỗi nghiệp vụ, thuộc tính `.code` và `.message`.
  - `BusinessRuleViolationError(DomainError)`.
  - `NotFoundError(message, code)`, `ConflictError(message, code)`, `PermissionDeniedError(message, code)`, `AuthenticationError(message, code)` — đều kế thừa `ApplicationError`.
  - `IClock` — protocol có `now() -> datetime` trả về thời điểm UTC có timezone.
  - `SystemClock` — implementation của `IClock`.

- [ ] **Step 1: Viết test cho Entity và exception**

File `backend/tests/unit/shared/test_entity.py`:

```python
from dataclasses import FrozenInstanceError, dataclass
from uuid import UUID

import pytest

from src.shared.domain.entity import Entity
from src.shared.domain.identifiers import new_id
from src.shared.domain.value_object import ValueObject


@dataclass(eq=False, kw_only=True)
class _EntityGiaLap(Entity):
    ten: str


@dataclass(frozen=True)
class _ValueObjectGiaLap(ValueObject):
    gia_tri: str


def test_hai_entity_cung_id_thi_bang_nhau() -> None:
    ma_dinh_danh: UUID = new_id()
    a = _EntityGiaLap(id=ma_dinh_danh, ten="A")
    b = _EntityGiaLap(id=ma_dinh_danh, ten="B khac hoan toan")

    assert a == b


def test_hai_entity_khac_id_thi_khac_nhau() -> None:
    a = _EntityGiaLap(id=new_id(), ten="Trung ten")
    b = _EntityGiaLap(id=new_id(), ten="Trung ten")

    assert a != b


def test_entity_dung_duoc_lam_khoa_cua_set() -> None:
    ma_dinh_danh = new_id()
    a = _EntityGiaLap(id=ma_dinh_danh, ten="A")
    b = _EntityGiaLap(id=ma_dinh_danh, ten="B")

    assert len({a, b}) == 1


def test_hai_loai_entity_khac_nhau_cung_id_van_khac_nhau() -> None:
    """Hai bảng khác nhau có thể tình cờ trùng id — chúng không phải một thứ."""

    @dataclass(eq=False, kw_only=True)
    class _LoaiKhac(Entity):
        ten: str

    ma_dinh_danh = new_id()

    assert _EntityGiaLap(id=ma_dinh_danh, ten="X") != _LoaiKhac(id=ma_dinh_danh, ten="X")


def test_so_sanh_voi_kieu_khong_phai_entity_tra_ve_false() -> None:
    assert _EntityGiaLap(id=new_id(), ten="A") != "khong-phai-entity"


def test_value_object_bang_nhau_khi_cung_gia_tri() -> None:
    assert _ValueObjectGiaLap(gia_tri="x") == _ValueObjectGiaLap(gia_tri="x")


def test_value_object_khong_the_thay_doi() -> None:
    vo = _ValueObjectGiaLap(gia_tri="x")
    with pytest.raises(FrozenInstanceError):
        vo.gia_tri = "y"  # type: ignore[misc]
```

File `backend/tests/unit/shared/test_exceptions.py`:

```python
import pytest

from src.shared.application.exceptions import (
    ApplicationError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.shared.domain.exceptions import BusinessRuleViolationError, DomainError


def test_domain_error_giu_lai_ma_loi_va_thong_diep() -> None:
    loi = DomainError("Khong hop le", code="INVALID")

    assert loi.code == "INVALID"
    assert loi.message == "Khong hop le"
    assert str(loi) == "Khong hop le"


def test_business_rule_violation_la_domain_error() -> None:
    assert issubclass(BusinessRuleViolationError, DomainError)


@pytest.mark.parametrize(
    "lop_loi",
    [NotFoundError, ConflictError, PermissionDeniedError, AuthenticationError],
)
def test_cac_loi_ung_dung_deu_ke_thua_application_error(
    lop_loi: type[ApplicationError],
) -> None:
    assert issubclass(lop_loi, ApplicationError)


@pytest.mark.parametrize(
    "lop_loi",
    [NotFoundError, ConflictError, PermissionDeniedError, AuthenticationError],
)
def test_loi_ung_dung_giu_lai_ma_loi_va_thong_diep(
    lop_loi: type[ApplicationError],
) -> None:
    """Tầng presentation đọc ``.code`` để ánh xạ sang mã HTTP — nếu thuộc tính
    này không được gán, toàn bộ xử lý lỗi của API sẽ hỏng."""
    loi = lop_loi("Thong diep thu", code="MA_THU")

    assert loi.message == "Thong diep thu"
    assert loi.code == "MA_THU"
    assert str(loi) == "Thong diep thu"
```

File `backend/tests/unit/shared/test_clock.py`:

```python
from datetime import UTC, datetime

from src.shared.infrastructure.clock import SystemClock


def test_tra_ve_thoi_diem_co_kem_mui_gio() -> None:
    """Thời điểm không kèm múi giờ sẽ làm hỏng mọi phép so sánh với cột
    ``timestamptz`` đọc từ cơ sở dữ liệu."""
    bay_gio = SystemClock().now()

    assert bay_gio.tzinfo is not None
    assert bay_gio.utcoffset() == UTC.utcoffset(None)


def test_thoi_gian_khong_lui_ve_qua_khu() -> None:
    truoc = SystemClock().now()
    sau = SystemClock().now()

    assert sau >= truoc


def test_gan_voi_thoi_gian_he_thong() -> None:
    lech = abs((SystemClock().now() - datetime.now(UTC)).total_seconds())

    assert lech < 5
```

File `backend/tests/unit/shared/test_identifiers.py`:

```python
from uuid import UUID

from src.shared.domain.identifiers import new_id


def test_new_id_tra_ve_uuid_phien_ban_7() -> None:
    ma = new_id()

    assert isinstance(ma, UUID)
    assert ma.version == 7


def test_hai_lan_goi_cho_hai_gia_tri_khac_nhau() -> None:
    assert new_id() != new_id()


def test_id_sinh_sau_lon_hon_id_sinh_truoc() -> None:
    """UUID v7 sắp xếp được theo thời gian — đây là lý do chọn v7 thay vì v4."""
    danh_sach = [new_id() for _ in range(100)]

    assert danh_sach == sorted(danh_sach)
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
cd backend
uv run pytest tests/unit/shared -v
```

Expected: FAIL với `ModuleNotFoundError: No module named 'src.shared'`.

- [ ] **Step 3: Viết `src/shared/domain/identifiers.py`**

```python
"""Sinh định danh cho entity."""

from uuid import UUID

import uuid_utils


def new_id() -> UUID:
    """Sinh UUID phiên bản 7 — ngẫu nhiên nhưng sắp xếp được theo thời gian.

    Thư viện chuẩn của Python 3.13 chỉ có tới ``uuid5``; ``uuid.uuid7()`` xuất
    hiện từ Python 3.14. Gói ``uuid_utils`` trả về kiểu UUID riêng của nó nên
    phải chuyển về ``uuid.UUID`` của thư viện chuẩn để SQLAlchemy và Pydantic
    làm việc được.

    Khi dự án nâng lên Python 3.14, chỉ cần đổi thân hàm này thành
    ``return uuid.uuid7()`` và gỡ dependency ``uuid-utils``.
    """
    return UUID(bytes=uuid_utils.uuid7().bytes)
```

- [ ] **Step 4: Viết `src/shared/domain/entity.py`**

```python
"""Lớp cơ sở cho entity trong tầng domain."""

from dataclasses import dataclass, field
from uuid import UUID

from src.shared.domain.identifiers import new_id


@dataclass(eq=False, kw_only=True)
class Entity:
    """Entity được định danh bằng ``id``, không phải bằng giá trị thuộc tính.

    Hai entity bằng nhau khi cùng ``id``, dù các thuộc tính khác khác nhau.
    """

    id: UUID = field(default_factory=new_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        if type(self) is not type(other):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.id))


@dataclass(eq=False, kw_only=True)
class AggregateRoot(Entity):
    """Entity đóng vai trò điểm vào của một aggregate.

    Repository chỉ làm việc với aggregate root, không truy cập trực tiếp
    các entity con bên trong aggregate.
    """
```

- [ ] **Step 4: Viết `src/shared/domain/value_object.py`**

```python
"""Lớp cơ sở cho value object trong tầng domain."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """Value object được định danh bằng giá trị, không có ``id``.

    Lớp con phải khai báo ``@dataclass(frozen=True)`` để giữ tính bất biến.
    """
```

- [ ] **Step 5: Viết `src/shared/domain/exceptions.py`**

```python
"""Lỗi thuộc tầng domain."""


class DomainError(Exception):
    """Lỗi gốc của mọi vi phạm quy tắc nghiệp vụ.

    ``code`` là mã ổn định dùng cho API và cho frontend đối chiếu; ``message``
    là thông điệp tiếng Việt hiển thị cho người dùng.
    """

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class BusinessRuleViolationError(DomainError):
    """Một quy tắc nghiệp vụ bị vi phạm."""
```

- [ ] **Step 6: Viết `src/shared/application/exceptions.py`**

```python
"""Lỗi thuộc tầng application."""


class ApplicationError(Exception):
    """Lỗi gốc của tầng application."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class NotFoundError(ApplicationError):
    """Không tìm thấy tài nguyên được yêu cầu."""


class ConflictError(ApplicationError):
    """Thao tác xung đột với trạng thái hiện tại của dữ liệu."""


class PermissionDeniedError(ApplicationError):
    """Người gọi đã xác thực nhưng không đủ quyền."""


class AuthenticationError(ApplicationError):
    """Người gọi chưa xác thực hoặc thông tin xác thực không hợp lệ."""
```

- [ ] **Step 7: Viết `src/shared/application/ports.py`**

```python
"""Port cho các phụ thuộc bên ngoài mà tầng application cần."""

from datetime import datetime
from typing import Protocol


class IClock(Protocol):
    """Nguồn thời gian.

    Tách thành port để test kiểm soát được thời gian mà không cần chờ đợi
    hay giả lập đồng hồ hệ thống.
    """

    def now(self) -> datetime:
        """Trả về thời điểm hiện tại theo UTC, luôn kèm thông tin timezone."""
        ...
```

- [ ] **Step 8: Viết `src/shared/infrastructure/clock.py`**

```python
"""Implementation của port thời gian."""

from datetime import UTC, datetime


class SystemClock:
    """Lấy thời gian từ đồng hồ hệ thống."""

    def now(self) -> datetime:
        return datetime.now(UTC)
```

- [ ] **Step 9: Tạo các file `__init__.py`**

```bash
cd backend
touch src/shared/__init__.py src/shared/domain/__init__.py \
      src/shared/application/__init__.py src/shared/infrastructure/__init__.py \
      tests/unit/shared/__init__.py
```

- [ ] **Step 10: Chạy test để xác nhận thành công**

```bash
uv run pytest tests/unit/shared -v
```

Expected: `23 passed` (một số test dùng `parametrize` nên nở ra nhiều trường hợp).

Kiểm tra độ phủ của shared kernel — đây là nền 18 task sau kế thừa:

```bash
uv run pytest tests/unit/shared --cov=src.shared --cov-report=term-missing
```

Expected: ≥ 90%.

- [ ] **Step 11: Kiểm tra type và dependency rule**

```bash
uv run mypy src
uv run ruff check .
```

Expected: `Success: no issues found`, `All checks passed!`.

- [ ] **Step 12: Commit**

```bash
git add backend/src/shared backend/tests/unit/shared
git commit -m "feat: add shared kernel with entity, value object, and error types"
```

---

## Task 3: Kết nối cơ sở dữ liệu, Alembic và Unit of Work

**Files:**
- Create: `backend/src/shared/infrastructure/event_loop.py`
- Create: `backend/src/shared/infrastructure/config.py`
- Create: `backend/src/shared/infrastructure/database.py`
- Create: `backend/src/shared/application/unit_of_work.py`
- Create: `backend/src/shared/infrastructure/sqlalchemy_uow.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/unit/shared/test_event_loop.py`
- Test: `backend/tests/integration/__init__.py`
- Test: `backend/tests/integration/test_database.py`

**Interfaces:**
- Consumes: `src.shared.application.exceptions` từ Task 2.
- Produces:
  - `cau_hinh_event_loop() -> None` — chuyển Windows sang `SelectorEventLoop`; không làm gì trên nền tảng khác. Mọi entry point async phải gọi trước khi tạo engine.
  - `Settings` — đọc cấu hình từ biến môi trường; thuộc tính `database_url`, `test_database_url`, `jwt_secret_key`, `jwt_algorithm`, `access_token_expire_minutes`, `refresh_token_expire_days`, `login_rate_limit_attempts`, `login_rate_limit_window_seconds`, `app_env`, `log_level`.
  - `get_settings() -> Settings` — có cache.
  - `Base` — lớp cơ sở khai báo cho mọi ORM model.
  - `create_engine_and_session_factory(database_url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]`.
  - `IUnitOfWork` — protocol có `__aenter__`, `__aexit__`, `commit()`, `rollback()`.
  - `SqlAlchemyUnitOfWork(session_factory)` — implementation, thuộc tính `.session` dùng được sau khi vào context.

- [ ] **Step 1: Tạo hai database**

```bash
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -c "CREATE DATABASE omnichat;"
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -c "CREATE DATABASE omnichat_test;"
```

Expected: `CREATE DATABASE` hai lần. Nếu báo `already exists` thì bỏ qua.

- [ ] **Step 2: Tạo `.env` từ mẫu**

```bash
cd backend
cp .env.example .env
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))"
```

Chép giá trị in ra, thay dòng `JWT_SECRET_KEY=` trong `.env`.

- [ ] **Step 2b: Viết test cho `event_loop.py`**

File `backend/tests/unit/shared/test_event_loop.py`:

```python
import asyncio
import sys

import pytest

from src.shared.infrastructure.event_loop import cau_hinh_event_loop


@pytest.mark.skipif(sys.platform != "win32", reason="Chỉ áp dụng cho Windows")
def test_tren_windows_chon_selector_event_loop() -> None:
    """psycopg từ chối ProactorEventLoop — nếu test này đỏ thì mọi test chạm
    cơ sở dữ liệu cũng sẽ đỏ theo."""
    cau_hinh_event_loop()

    assert isinstance(
        asyncio.get_event_loop_policy(), asyncio.WindowsSelectorEventLoopPolicy
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Chỉ áp dụng cho Linux/macOS")
def test_ngoai_windows_khong_doi_gi() -> None:
    truoc = asyncio.get_event_loop_policy()

    cau_hinh_event_loop()

    assert asyncio.get_event_loop_policy() is truoc


def test_goi_nhieu_lan_khong_gay_loi() -> None:
    cau_hinh_event_loop()
    cau_hinh_event_loop()
```

- [ ] **Step 3: Viết test integration cho kết nối và Unit of Work**

File `backend/tests/integration/test_database.py`:

```python
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.shared.infrastructure.sqlalchemy_uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


async def test_ket_noi_duoc_toi_postgres(db_session: AsyncSession) -> None:
    ket_qua = await db_session.execute(text("SELECT 1"))

    assert ket_qua.scalar_one() == 1


async def test_postgres_dung_phien_ban_17_tro_len(db_session: AsyncSession) -> None:
    ket_qua = await db_session.execute(text("SHOW server_version_num"))
    phien_ban = int(ket_qua.scalar_one())

    assert phien_ban >= 170000


async def test_unit_of_work_commit_thi_du_lieu_duoc_luu(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.session.execute(
            text("CREATE TEMP TABLE thu_nghiem (gia_tri int) ON COMMIT PRESERVE ROWS")
        )
        await uow.session.execute(text("INSERT INTO thu_nghiem VALUES (42)"))
        await uow.commit()

        ket_qua = await uow.session.execute(text("SELECT gia_tri FROM thu_nghiem"))
        assert ket_qua.scalar_one() == 42


async def test_unit_of_work_tu_rollback_khi_co_ngoai_le(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    class LoiGiaLapError(Exception):
        pass

    with pytest.raises(LoiGiaLapError):
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.session.execute(text("CREATE TEMP TABLE thu_nghiem_2 (gia_tri int)"))
            await uow.session.execute(text("INSERT INTO thu_nghiem_2 VALUES (1)"))
            raise LoiGiaLapError

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        ket_qua = await uow.session.execute(
            text("SELECT to_regclass('pg_temp.thu_nghiem_2') IS NULL")
        )
        assert ket_qua.scalar_one() is True
```

- [ ] **Step 4: Chạy test để xác nhận thất bại**

```bash
uv run pytest tests/integration -v
```

Expected: FAIL với `ModuleNotFoundError` hoặc `fixture 'db_session' not found`.

- [ ] **Step 4b: Viết `src/shared/infrastructure/event_loop.py`**

```python
"""Cấu hình event loop cho từng nền tảng."""

import asyncio
import sys


def cau_hinh_event_loop() -> None:
    """Chuyển Windows sang ``SelectorEventLoop`` trước khi mở kết nối async.

    Từ Python 3.8, event loop mặc định của Windows là ``ProactorEventLoop``.
    psycopg từ chối chạy trên nó và ném ``InterfaceError: Psycopg cannot use
    the 'ProactorEventLoop' to run in async mode``. Đây là hạn chế đã biết của
    driver, không phải lỗi cấu hình.

    Mọi entry point chạy code async phải gọi hàm này **trước khi** tạo engine:
    ``tests/conftest.py``, ``migrations/env.py``, ``src/main.py``, và các script
    trong ``scripts/``. Gọi nhiều lần không gây hại.

    Trên Linux và macOS hàm này không làm gì — nơi triển khai thật sẽ chạy
    Linux, nên chi phí bằng không ở môi trường sản xuất.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

- [ ] **Step 5: Viết `src/shared/infrastructure/config.py`**

```python
"""Cấu hình ứng dụng đọc từ biến môi trường."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Toàn bộ cấu hình của ứng dụng.

    Giá trị lấy từ biến môi trường, hoặc từ file ``.env`` khi chạy cục bộ.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    test_database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300

    app_env: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Trả về cấu hình đã cache, tránh đọc lại file ``.env`` mỗi lần gọi."""
    return Settings()  # type: ignore[call-arg]
```

- [ ] **Step 6: Viết `src/shared/infrastructure/database.py`**

```python
"""Engine và session factory cho SQLAlchemy async."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Lớp cơ sở khai báo cho mọi ORM model."""


def create_engine_and_session_factory(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Tạo engine async và session factory tương ứng.

    ``expire_on_commit=False`` để đối tượng vẫn đọc được sau khi commit —
    cần thiết vì mapper chuyển ORM model sang domain entity sau khi commit.
    """
    engine = create_async_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine, session_factory
```

- [ ] **Step 7: Viết `src/shared/application/unit_of_work.py`**

```python
"""Port Unit of Work."""

from types import TracebackType
from typing import Protocol, Self


class IUnitOfWork(Protocol):
    """Gom nhiều thao tác ghi vào một giao dịch nguyên tử.

    Khi thoát context mà chưa gọi ``commit()``, mọi thay đổi bị rollback.
    """

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
```

- [ ] **Step 8: Viết `src/shared/infrastructure/sqlalchemy_uow.py`**

```python
"""Unit of Work dựa trên SQLAlchemy AsyncSession."""

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SqlAlchemyUnitOfWork:
    """Quản lý vòng đời của một ``AsyncSession``.

    Mặc định rollback khi thoát context, nên quên gọi ``commit()`` sẽ không
    ghi nhầm dữ liệu.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Phải vào context của Unit of Work trước khi dùng session.")
        return self._session

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                await self.session.rollback()
        finally:
            await self.session.close()
            self._session = None

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
```

- [ ] **Step 9: Viết `backend/tests/conftest.py`**

```python
"""Fixture dùng chung cho toàn bộ test."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.shared.infrastructure.config import get_settings
from src.shared.infrastructure.database import create_engine_and_session_factory
from src.shared.infrastructure.event_loop import cau_hinh_event_loop

# Phải chạy trước khi pytest-asyncio tạo event loop đầu tiên, nếu không psycopg
# sẽ từ chối chạy trên ProactorEventLoop của Windows.
cau_hinh_event_loop()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return get_settings().test_database_url


@pytest.fixture(scope="session")
async def engine(test_database_url: str) -> AsyncIterator[AsyncEngine]:
    engine, _ = create_engine_and_session_factory(test_database_url)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Session bị rollback sau mỗi test, nên các test không ảnh hưởng lẫn nhau."""
    async with session_factory() as session:
        yield session
        await session.rollback()
```

- [ ] **Step 10: Chạy test integration**

```bash
cd backend
touch tests/integration/__init__.py
uv run pytest tests/integration -v
```

Expected: `4 passed`.

Nếu lỗi `password authentication failed`, sửa `DATABASE_URL` và `TEST_DATABASE_URL` trong `.env` để thêm mật khẩu:
`postgresql+psycopg://postgres:<mat-khau>@localhost:5432/omnichat`.

- [ ] **Step 11: Khởi tạo Alembic**

```bash
uv run alembic init -t async migrations
```

Lệnh này tạo `alembic.ini` và thư mục `migrations/`.

- [ ] **Step 12: Sửa `backend/alembic.ini`**

Tìm dòng `sqlalchemy.url = ...` và thay bằng chuỗi rỗng — URL sẽ được nạp từ `.env` trong `env.py`:

```ini
sqlalchemy.url =
```

- [ ] **Step 13: Sửa `backend/migrations/env.py`**

Thay toàn bộ nội dung file bằng:

```python
"""Cấu hình môi trường migration của Alembic."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.shared.infrastructure.config import get_settings
from src.shared.infrastructure.database import Base
from src.shared.infrastructure.event_loop import cau_hinh_event_loop

# Alembic gọi asyncio.run() để chạy migration — cần đúng loại event loop mà
# psycopg chấp nhận, giống mọi entry point async khác.
cau_hinh_event_loop()

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Import `Base` ở đây là điều bắt buộc: Alembic cần `Base.metadata` để so sánh schema. Các ORM model sẽ được import trong Task 9 để autogenerate nhìn thấy chúng.

- [ ] **Step 14: Xác nhận Alembic chạy được**

```bash
uv run alembic current
```

Expected: không báo lỗi, in ra dòng trống hoặc thông tin revision hiện tại (chưa có migration nào).

- [ ] **Step 15: Chạy toàn bộ kiểm tra**

```bash
uv run pytest -v
uv run mypy src
uv run ruff check .
uv run lint-imports
```

Expected: toàn bộ xanh. `lint-imports` in `Contracts: 3 kept, 0 broken.`

- [ ] **Step 16: Commit**

```bash
git add backend/src/shared backend/tests backend/alembic.ini backend/migrations
git commit -m "feat: add database connection, unit of work, and alembic setup"
```

---

## Các giai đoạn tiếp theo

- [Phần 2 — Domain Identity](2026-07-21-omnichat-foundation-part2-domain.md) (Task 4–8)
- [Phần 3 — Hạ tầng lưu trữ](2026-07-21-omnichat-foundation-part3-infra.md) (Task 9–12)
- [Phần 4 — Use case và API](2026-07-21-omnichat-foundation-part4-api.md) (Task 13–20)
