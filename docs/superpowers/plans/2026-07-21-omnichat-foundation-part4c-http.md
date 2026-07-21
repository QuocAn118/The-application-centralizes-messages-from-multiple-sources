# OmniChat Foundation — Phần 4c: FastAPI và router (Task 16–18)

> Tiếp nối [phần 4b](2026-07-21-omnichat-foundation-part4b-admin-usecases.md). Global Constraints ở [phần 1](2026-07-21-omnichat-foundation.md) áp dụng cho mọi task tại đây.

---

## Task 16: FastAPI app, dependency và exception handler

**Files:**
- Create: `backend/src/shared/infrastructure/logging.py`
- Create: `backend/src/modules/identity/presentation/__init__.py`
- Create: `backend/src/modules/identity/presentation/schemas/__init__.py`
- Create: `backend/src/modules/identity/presentation/schemas/common.py`
- Create: `backend/src/modules/identity/presentation/dependencies.py`
- Create: `backend/src/main.py`
- Test: `backend/tests/e2e/__init__.py`
- Test: `backend/tests/e2e/conftest.py`
- Test: `backend/tests/e2e/test_app.py`

**Interfaces:**
- Consumes: mọi use case (Task 13–15), repository (Task 11), bảo mật (Task 12).
- Produces:
  - `create_app() -> FastAPI` — composition root, dùng được cả cho production lẫn test.
  - `get_session() -> AsyncIterator[AsyncSession]` — dependency mở session theo từng request.
  - `get_current_user(...) -> User` — giải mã token, nạp người dùng, chặn tài khoản bị vô hiệu hoá.
  - `require_role(*roles: Role)` — dependency factory chặn theo vai trò.
  - `require_password_changed(...) -> User` — chặn người dùng chưa đổi mật khẩu tạm.
  - `ErrorResponse`, `ErrorDetail` — Pydantic schema cho lỗi.
  - `PageResponse[T]` — Pydantic schema phân trang.

**Ba tầng phân quyền, mỗi tầng một nhiệm vụ:**

`require_role` chặn theo vai trò ở tầng route — rẻ và chặn sớm. Use case xử lý câu hỏi phụ thuộc dữ liệu. Domain entity giữ bất biến. Không tầng nào thay được tầng nào.

- [ ] **Step 1: Viết `shared/infrastructure/logging.py`**

```python
"""Cấu hình log dạng JSON kèm mã định danh request."""

import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger.json import JsonFormatter

# Mã định danh request, gắn theo từng luồng xử lý bất đồng bộ để mọi dòng log
# của cùng một request đều truy vết được với nhau.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class _BoLocRequestId(logging.Filter):
    """Gắn ``request_id`` vào mọi bản ghi log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def cau_hinh_logging(log_level: str = "INFO") -> None:
    """Cấu hình log gốc.

    Xuất JSON để hệ thống thu thập log phân tích được, thay vì phải viết biểu
    thức chính quy trên chuỗi tự do.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
            rename_fields={"asctime": "thoi_diem", "levelname": "muc_do"},
        )
    )
    handler.addFilter(_BoLocRequestId())

    goc = logging.getLogger()
    goc.handlers.clear()
    goc.addHandler(handler)
    goc.setLevel(log_level.upper())
```

- [ ] **Step 2: Viết `presentation/schemas/common.py`**

```python
"""Schema dùng chung cho phản hồi HTTP."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Chi tiết một lỗi."""

    code: str = Field(description="Mã lỗi ổn định, dùng để đối chiếu ở client")
    message: str = Field(description="Thông điệp tiếng Việt hiển thị cho người dùng")
    details: dict[str, Any] | None = Field(default=None)


class ErrorResponse(BaseModel):
    """Định dạng lỗi thống nhất cho toàn bộ API."""

    error: ErrorDetail
    request_id: str


class PageResponse[T](BaseModel):
    """Một trang kết quả."""

    items: list[T]
    total: int
    limit: int
    offset: int
```

- [ ] **Step 3: Viết `presentation/dependencies.py`**

```python
"""Ghép nối phụ thuộc cho tầng HTTP."""

from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.ports import (
    ExpiredTokenError,
    InvalidTokenError,
)
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.identity.infrastructure.security.password_hasher import (
    BcryptPasswordHasher,
)
from src.modules.identity.infrastructure.security.token_service import JwtTokenService
from src.shared.application.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
)
from src.shared.infrastructure.clock import SystemClock
from src.shared.infrastructure.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Mở một session cho mỗi request.

    Commit khi xử lý xong mà không có lỗi; rollback nếu có. Nhờ vậy router
    không phải tự quản lý giao dịch, và một request luôn là một giao dịch.
    """
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_clock() -> SystemClock:
    return SystemClock()


def get_password_hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()


def get_token_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JwtTokenService:
    return JwtTokenService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        clock=SystemClock(),
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    token_service: Annotated[JwtTokenService, Depends(get_token_service)],
) -> User:
    """Xác định người gọi từ access token.

    Có tra cứu cơ sở dữ liệu để nạp thực thể ``User`` đầy đủ — các use case cần
    nó để kiểm tra quyền theo dữ liệu. Việc này cũng khiến tài khoản vừa bị vô
    hiệu hoá mất quyền ngay ở lần gọi tiếp theo, dù access token còn hạn.
    """
    if credentials is None:
        raise AuthenticationError(
            "Thiếu thông tin xác thực.", code="MISSING_CREDENTIALS"
        )

    try:
        payload = token_service.decode_access_token(credentials.credentials)
    except (InvalidTokenError, ExpiredTokenError):
        raise

    user = await SqlAlchemyUserRepository(session).get_by_id(payload.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError(
            "Tài khoản không còn hiệu lực.", code="INACTIVE_ACCOUNT"
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_session)]


def require_role(*roles: Role) -> Callable[[User], User]:
    """Chặn sớm theo vai trò ở tầng route.

    Chỉ trả lời được câu hỏi "vai trò này có được gọi endpoint này không".
    Câu hỏi "người này có được thao tác lên bản ghi kia không" thuộc về use
    case, nơi biết dữ liệu cụ thể.
    """

    def _kiem_tra(user: CurrentUser) -> User:
        if user.role not in roles:
            raise PermissionDeniedError(
                "Bạn không có quyền thực hiện thao tác này.",
                code="INSUFFICIENT_ROLE",
            )
        return user

    return _kiem_tra


def require_password_changed(user: CurrentUser) -> User:
    """Buộc đổi mật khẩu tạm trước khi dùng các chức năng khác."""
    if user.must_change_password:
        raise PermissionDeniedError(
            "Bạn phải đổi mật khẩu trước khi tiếp tục.",
            code="PASSWORD_CHANGE_REQUIRED",
        )
    return user
```

- [ ] **Step 4: Viết `src/main.py`**

```python
"""Điểm khởi tạo ứng dụng."""

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.modules.identity.application.ports import (
    ExpiredTokenError,
    InvalidTokenError,
)
from src.shared.application.exceptions import (
    ApplicationError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.shared.domain.exceptions import DomainError
from src.shared.infrastructure.config import get_settings
from src.shared.infrastructure.database import create_engine_and_session_factory
from src.shared.infrastructure.logging import cau_hinh_logging, request_id_var

logger = logging.getLogger(__name__)

# Ánh xạ loại lỗi sang mã HTTP. Đặt tập trung ở đây để mọi endpoint trả lỗi
# nhất quán mà không phải bắt ngoại lệ trong từng router.
_MA_HTTP: list[tuple[type[Exception], int]] = [
    (AuthenticationError, 401),
    (InvalidTokenError, 401),
    (ExpiredTokenError, 401),
    (PermissionDeniedError, 403),
    (NotFoundError, 404),
    (ConflictError, 409),
    (DomainError, 422),
    (ApplicationError, 400),
]


def _tra_ma_http(loi: Exception) -> int:
    for lop, ma in _MA_HTTP:
        if isinstance(loi, lop):
            return ma
    return 500


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Mở kết nối cơ sở dữ liệu khi khởi động, đóng khi tắt."""
    settings = get_settings()
    engine, session_factory = create_engine_and_session_factory(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = session_factory
    logger.info("Ứng dụng đã khởi động", extra={"moi_truong": settings.app_env})
    yield
    await engine.dispose()
    logger.info("Ứng dụng đã dừng")


def create_app() -> FastAPI:
    """Dựng ứng dụng.

    Là composition root: mọi thứ được ghép nối tại đây và chỉ tại đây.
    """
    settings = get_settings()
    cau_hinh_logging(settings.log_level)

    app = FastAPI(
        title="OmniChat API",
        version="0.1.0",
        description="Nền tảng tập trung tin nhắn đa kênh",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def gan_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Gắn mã định danh cho mỗi request để truy vết log."""
        ma = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_var.set(ma)
        phan_hoi = await call_next(request)
        phan_hoi.headers["X-Request-ID"] = ma
        return phan_hoi

    @app.middleware("http")
    async def them_security_header(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Thêm các header bảo mật cơ bản.

        API chỉ trả JSON nên rủi ro XSS thấp, nhưng ``nosniff`` và
        ``X-Frame-Options`` vẫn cần để trình duyệt không diễn giải sai phản hồi.
        """
        phan_hoi = await call_next(request)
        phan_hoi.headers["X-Content-Type-Options"] = "nosniff"
        phan_hoi.headers["X-Frame-Options"] = "DENY"
        phan_hoi.headers["Referrer-Policy"] = "no-referrer"
        return phan_hoi

    @app.exception_handler(DomainError)
    @app.exception_handler(ApplicationError)
    async def xu_ly_loi_nghiep_vu(request: Request, exc: Exception) -> JSONResponse:
        ma_http = _tra_ma_http(exc)
        ma_loi = getattr(exc, "code", "UNKNOWN_ERROR")
        thong_diep = getattr(exc, "message", str(exc))
        return JSONResponse(
            status_code=ma_http,
            content={
                "error": {"code": ma_loi, "message": thong_diep, "details": None},
                "request_id": request_id_var.get(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def xu_ly_loi_du_lieu(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Dữ liệu gửi lên không hợp lệ.",
                    "details": {"cac_loi": exc.errors()},
                },
                "request_id": request_id_var.get(),
            },
        )

    @app.exception_handler(Exception)
    async def xu_ly_loi_khong_luong_truoc(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Không để lộ chi tiết lỗi hệ thống ra ngoài.

        Nội dung lỗi được ghi vào log kèm ``request_id`` để tra cứu; client chỉ
        nhận thông điệp chung.
        """
        logger.exception("Lỗi không lường trước", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Đã xảy ra lỗi hệ thống.",
                    "details": None,
                },
                "request_id": request_id_var.get(),
            },
        )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Kiểm tra tiến trình còn sống."""
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    async def health_ready(request: Request) -> JSONResponse:
        """Kiểm tra ứng dụng sẵn sàng nhận tải, gồm cả kết nối cơ sở dữ liệu."""
        try:
            async with request.app.state.session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception:
            logger.exception("Kiểm tra sẵn sàng thất bại")
            return JSONResponse(
                status_code=503,
                content={"status": "khong_san_sang", "database": "loi"},
            )
        return JSONResponse(
            status_code=200, content={"status": "ok", "database": "ok"}
        )

    # Router được đăng ký ở Task 17 và 18.
    from src.modules.identity.presentation.routers.auth_router import (
        router as auth_router,
    )
    from src.modules.identity.presentation.routers.department_router import (
        router as department_router,
    )
    from src.modules.identity.presentation.routers.user_router import (
        router as user_router,
    )

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(user_router, prefix="/api/v1")
    app.include_router(department_router, prefix="/api/v1")

    return app


app = create_app()
```

**Lưu ý thứ tự triển khai:** khối import router ở cuối `create_app` sẽ lỗi cho tới khi Task 17 và 18 xong. Khi làm Task 16, tạm bỏ khối đó và ba dòng `include_router`, rồi thêm lại ở Task 18 Step cuối.

- [ ] **Step 5: Viết `tests/e2e/conftest.py`**

```python
"""Fixture cho test đầu-cuối."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.main import create_app
from src.shared.infrastructure.config import get_settings
from src.shared.infrastructure.database import create_engine_and_session_factory


@pytest.fixture
async def app_test(engine: AsyncEngine):  # type: ignore[no-untyped-def]
    """Ứng dụng trỏ vào cơ sở dữ liệu test.

    Ghi đè ``session_factory`` để test không chạm vào dữ liệu phát triển.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    ung_dung = create_app()
    ung_dung.state.engine = engine
    ung_dung.state.session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return ung_dung


@pytest.fixture
async def client(app_test) -> AsyncIterator[AsyncClient]:  # type: ignore[no-untyped-def]
    async with AsyncClient(
        transport=ASGITransport(app=app_test), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(autouse=True)
async def don_du_lieu(engine: AsyncEngine) -> AsyncIterator[None]:
    """Xoá sạch dữ liệu trước mỗi test đầu-cuối.

    Test đầu-cuối đi qua nhiều giao dịch nên không dùng được cách rollback như
    test tích hợp; phải dọn bảng một cách tường minh.
    """
    yield
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE audit_logs, refresh_tokens, users, departments "
                "RESTART IDENTITY CASCADE"
            )
        )
```

- [ ] **Step 6: Viết test cho ứng dụng**

File `backend/tests/e2e/test_app.py`:

```python
import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


class TestKiemTraSucKhoe:
    async def test_health_tra_ve_ok(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/health")

        assert phan_hoi.status_code == 200
        assert phan_hoi.json() == {"status": "ok"}

    async def test_health_ready_kiem_tra_co_so_du_lieu(
        self, client: AsyncClient
    ) -> None:
        phan_hoi = await client.get("/health/ready")

        assert phan_hoi.status_code == 200
        assert phan_hoi.json()["database"] == "ok"


class TestHeaderBaoMat:
    async def test_co_day_du_header_bao_mat(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/health")

        assert phan_hoi.headers["X-Content-Type-Options"] == "nosniff"
        assert phan_hoi.headers["X-Frame-Options"] == "DENY"
        assert phan_hoi.headers["Referrer-Policy"] == "no-referrer"


class TestMaDinhDanhRequest:
    async def test_moi_phan_hoi_deu_co_request_id(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/health")

        assert phan_hoi.headers.get("X-Request-ID")

    async def test_giu_nguyen_request_id_do_client_gui(
        self, client: AsyncClient
    ) -> None:
        phan_hoi = await client.get(
            "/health", headers={"X-Request-ID": "ma-tu-client-123"}
        )

        assert phan_hoi.headers["X-Request-ID"] == "ma-tu-client-123"


class TestDinhDangLoi:
    async def test_khong_tim_thay_duong_dan(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/api/v1/duong-dan-khong-ton-tai")

        assert phan_hoi.status_code == 404

    async def test_thieu_token_tra_ve_401_dung_dinh_dang(
        self, client: AsyncClient
    ) -> None:
        phan_hoi = await client.get("/api/v1/auth/me")

        assert phan_hoi.status_code == 401
        noi_dung = phan_hoi.json()
        assert noi_dung["error"]["code"] == "MISSING_CREDENTIALS"
        assert "request_id" in noi_dung

    async def test_token_rac_tra_ve_401(self, client: AsyncClient) -> None:
        phan_hoi = await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer token-bia-dat"}
        )

        assert phan_hoi.status_code == 401
        assert phan_hoi.json()["error"]["code"] == "INVALID_TOKEN"


class TestTaiLieuApi:
    async def test_co_openapi_schema(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/openapi.json")

        assert phan_hoi.status_code == 200
        assert phan_hoi.json()["info"]["title"] == "OmniChat API"
```

- [ ] **Step 7: Chạy test (sau khi Task 17–18 xong)**

```bash
cd backend
mkdir -p src/modules/identity/presentation/schemas tests/e2e
touch src/modules/identity/presentation/__init__.py \
      src/modules/identity/presentation/schemas/__init__.py \
      tests/e2e/__init__.py
uv run pytest tests/e2e/test_app.py -v
```

Expected: `9 passed`. Nếu chưa làm Task 17–18 thì các test cần `/api/v1/auth/me` sẽ đỏ — điều đó đúng ở giai đoạn này.

- [ ] **Step 8: Commit**

```bash
git add backend/src/main.py backend/src/shared/infrastructure/logging.py \
        backend/src/modules/identity/presentation backend/tests/e2e
git commit -m "feat: add fastapi app with error handling and auth dependencies"
```

---

## Task 17: Router xác thực

**Files:**
- Create: `backend/src/modules/identity/presentation/schemas/auth_schemas.py`
- Create: `backend/src/modules/identity/presentation/routers/__init__.py`
- Create: `backend/src/modules/identity/presentation/routers/auth_router.py`
- Test: `backend/tests/e2e/test_auth_api.py`

**Interfaces:**
- Consumes: use case xác thực (Task 13), dependency (Task 16).
- Produces:
  - `POST /api/v1/auth/login` → `TokenResponse`.
  - `POST /api/v1/auth/refresh` → `TokenResponse`.
  - `POST /api/v1/auth/logout` → 204.
  - `POST /api/v1/auth/change-password` → 204.
  - `GET /api/v1/auth/me` → `UserResponse`.

- [ ] **Step 1: Viết `schemas/auth_schemas.py`**

```python
"""Schema cho các endpoint xác thực."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.modules.identity.domain.entities.user import User


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int = Field(description="Số giây còn lại của access token")
    must_change_password: bool = Field(
        default=False,
        description="Nếu đúng, client phải chuyển sang màn hình đổi mật khẩu",
    )


class UserResponse(BaseModel):
    """Thông tin người dùng trả về cho client.

    Cố ý không có ``password_hash`` — dùng schema riêng thay vì trả thẳng
    entity là cách chắc chắn nhất để dữ liệu nhạy cảm không lọt ra ngoài.
    """

    id: UUID
    email: str
    full_name: str
    phone: str | None
    role: str
    department_id: UUID | None
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email.value,
            full_name=user.full_name,
            phone=user.phone,
            role=user.role.value,
            department_id=user.department_id,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )
```

- [ ] **Step 2: Viết `routers/auth_router.py`**

```python
"""Endpoint xác thực."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from src.modules.identity.application.use_cases.change_password import ChangePassword
from src.modules.identity.application.use_cases.login_user import LoginUser
from src.modules.identity.application.use_cases.logout_user import LogoutUser
from src.modules.identity.application.use_cases.refresh_access_token import (
    RefreshAccessToken,
)
from src.modules.identity.infrastructure.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)
from src.modules.identity.infrastructure.repositories.refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.identity.infrastructure.security.password_hasher import (
    BcryptPasswordHasher,
)
from src.modules.identity.infrastructure.security.token_service import JwtTokenService
from src.modules.identity.presentation.dependencies import (
    CurrentUser,
    DbSession,
    get_password_hasher,
    get_token_service,
)
from src.modules.identity.presentation.schemas.auth_schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from src.shared.infrastructure.clock import SystemClock
from src.shared.infrastructure.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _dia_chi_goi(request: Request) -> str | None:
    """Lấy địa chỉ IP của client.

    Ưu tiên ``X-Forwarded-For`` vì ứng dụng chạy sau reverse proxy. Header này
    do client gửi nên có thể giả mạo — chỉ dùng để ghi nhật ký, không dùng cho
    quyết định bảo mật.
    """
    chuyen_tiep = request.headers.get("X-Forwarded-For")
    if chuyen_tiep:
        return chuyen_tiep.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/login", response_model=TokenResponse)
async def dang_nhap(
    du_lieu: LoginRequest,
    request: Request,
    session: DbSession,
    hasher: Annotated[BcryptPasswordHasher, Depends(get_password_hasher)],
    token_service: Annotated[JwtTokenService, Depends(get_token_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Đăng nhập bằng email và mật khẩu."""
    use_case = LoginUser(
        user_repo=SqlAlchemyUserRepository(session),
        refresh_token_repo=SqlAlchemyRefreshTokenRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        hasher=hasher,
        token_service=token_service,
        clock=SystemClock(),
        refresh_token_expire_days=settings.refresh_token_expire_days,
    )
    ket_qua = await use_case.execute(
        email=du_lieu.email,
        password=du_lieu.password,
        ip_address=_dia_chi_goi(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return TokenResponse(
        access_token=ket_qua.tokens.access_token,
        refresh_token=ket_qua.tokens.refresh_token,
        token_type=ket_qua.tokens.token_type,
        expires_in=ket_qua.tokens.expires_in,
        must_change_password=ket_qua.must_change_password,
    )


@router.post("/refresh", response_model=TokenResponse)
async def lam_moi_token(
    du_lieu: RefreshRequest,
    request: Request,
    session: DbSession,
    token_service: Annotated[JwtTokenService, Depends(get_token_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Đổi refresh token lấy cặp token mới."""
    use_case = RefreshAccessToken(
        user_repo=SqlAlchemyUserRepository(session),
        refresh_token_repo=SqlAlchemyRefreshTokenRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        token_service=token_service,
        clock=SystemClock(),
        refresh_token_expire_days=settings.refresh_token_expire_days,
    )
    cap_token = await use_case.execute(
        refresh_token=du_lieu.refresh_token,
        ip_address=_dia_chi_goi(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return TokenResponse(
        access_token=cap_token.access_token,
        refresh_token=cap_token.refresh_token,
        token_type=cap_token.token_type,
        expires_in=cap_token.expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def dang_xuat(
    du_lieu: LogoutRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
    token_service: Annotated[JwtTokenService, Depends(get_token_service)],
) -> Response:
    """Thu hồi refresh token của phiên hiện tại."""
    use_case = LogoutUser(
        refresh_token_repo=SqlAlchemyRefreshTokenRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        token_service=token_service,
        clock=SystemClock(),
    )
    await use_case.execute(refresh_token=du_lieu.refresh_token, requester=nguoi_goi)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def doi_mat_khau(
    du_lieu: ChangePasswordRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
    hasher: Annotated[BcryptPasswordHasher, Depends(get_password_hasher)],
) -> Response:
    """Đổi mật khẩu của chính mình.

    Không yêu cầu ``require_password_changed``: người vừa được cấp mật khẩu
    tạm phải gọi được endpoint này, nếu không họ sẽ bị kẹt.
    """
    use_case = ChangePassword(
        user_repo=SqlAlchemyUserRepository(session),
        refresh_token_repo=SqlAlchemyRefreshTokenRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        hasher=hasher,
        clock=SystemClock(),
    )
    await use_case.execute(
        requester=nguoi_goi,
        current_password=du_lieu.current_password,
        new_password=du_lieu.new_password,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
async def thong_tin_cua_toi(nguoi_goi: CurrentUser) -> UserResponse:
    """Thông tin hồ sơ của người đang đăng nhập."""
    return UserResponse.from_entity(nguoi_goi)
```

- [ ] **Step 3: Viết test đầu-cuối cho xác thực**

File `backend/tests/e2e/test_auth_api.py`:

```python
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU = "MatKhauDung123"


async def _tao_admin(engine: AsyncEngine, email: str = "admin@congty.vn") -> None:
    """Tạo sẵn một quản trị viên bằng câu lệnh trực tiếp."""
    from src.modules.identity.infrastructure.security.password_hasher import (
        BcryptPasswordHasher,
    )
    from src.shared.domain.identifiers import new_id

    chuoi_hash = BcryptPasswordHasher(rounds=4).hash(MAT_KHAU)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, full_name, phone, role, "
                "department_id, is_active, must_change_password, last_login_at, "
                "created_at, updated_at) VALUES (:id, :email, :hash, 'Quản trị viên', "
                "NULL, 'ADMIN', NULL, true, false, NULL, now(), now())"
            ),
            {"id": new_id(), "email": email, "hash": chuoi_hash},
        )


class TestDangNhap:
    async def test_dang_nhap_thanh_cong(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)

        phan_hoi = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )

        assert phan_hoi.status_code == 200
        noi_dung = phan_hoi.json()
        assert noi_dung["access_token"]
        assert noi_dung["refresh_token"]
        assert noi_dung["token_type"] == "bearer"
        assert noi_dung["expires_in"] == 15 * 60

    async def test_mat_khau_sai_tra_ve_400(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)

        phan_hoi = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": "SaiRoi123"},
        )

        assert phan_hoi.status_code == 400
        assert phan_hoi.json()["error"]["code"] == "INVALID_CREDENTIALS"

    async def test_email_khong_ton_tai_cho_cung_ma_loi(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        """Không được để lộ email nào có trong hệ thống."""
        await _tao_admin(engine)

        phan_hoi = await client.post(
            "/api/v1/auth/login",
            json={"email": "khongton@tai.vn", "password": MAT_KHAU},
        )

        assert phan_hoi.status_code == 400
        assert phan_hoi.json()["error"]["code"] == "INVALID_CREDENTIALS"

    async def test_email_sai_dinh_dang_tra_ve_422(self, client: AsyncClient) -> None:
        phan_hoi = await client.post(
            "/api/v1/auth/login",
            json={"email": "khong-phai-email", "password": MAT_KHAU},
        )

        assert phan_hoi.status_code == 422

    async def test_phan_hoi_khong_chua_hash_mat_khau(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)

        phan_hoi = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )

        assert "password_hash" not in phan_hoi.text
        assert "$2b$" not in phan_hoi.text


class TestThongTinCuaToi:
    async def test_lay_duoc_ho_so_khi_co_token(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        token = dang_nhap.json()["access_token"]

        phan_hoi = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert phan_hoi.status_code == 200
        assert phan_hoi.json()["email"] == "admin@congty.vn"
        assert phan_hoi.json()["role"] == "ADMIN"

    async def test_khong_tra_ve_hash_mat_khau(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        token = dang_nhap.json()["access_token"]

        phan_hoi = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert "password_hash" not in phan_hoi.json()


class TestLamMoiToken:
    async def test_lam_moi_tra_ve_cap_token_moi(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        cu = dang_nhap.json()["refresh_token"]

        phan_hoi = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": cu}
        )

        assert phan_hoi.status_code == 200
        assert phan_hoi.json()["refresh_token"] != cu

    async def test_dung_lai_token_cu_bi_tu_choi(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        cu = dang_nhap.json()["refresh_token"]
        await client.post("/api/v1/auth/refresh", json={"refresh_token": cu})

        phan_hoi = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": cu}
        )

        assert phan_hoi.status_code == 401

    async def test_tai_su_dung_thu_hoi_ca_chuoi(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        """Token bị tái sử dụng nghĩa là đã lộ — cả chuỗi mất hiệu lực."""
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        cu = dang_nhap.json()["refresh_token"]
        lam_moi = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": cu}
        )
        moi = lam_moi.json()["refresh_token"]

        await client.post("/api/v1/auth/refresh", json={"refresh_token": cu})

        phan_hoi = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": moi}
        )
        assert phan_hoi.status_code == 401


class TestDangXuat:
    async def test_dang_xuat_thu_hoi_token(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        access = dang_nhap.json()["access_token"]
        refresh = dang_nhap.json()["refresh_token"]

        phan_hoi = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh},
            headers={"Authorization": f"Bearer {access}"},
        )

        assert phan_hoi.status_code == 204
        lam_moi = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh}
        )
        assert lam_moi.status_code == 401


class TestDoiMatKhau:
    async def test_doi_mat_khau_thanh_cong(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        access = dang_nhap.json()["access_token"]

        phan_hoi = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": MAT_KHAU, "new_password": "MatKhauMoi456"},
            headers={"Authorization": f"Bearer {access}"},
        )

        assert phan_hoi.status_code == 204
        lai = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": "MatKhauMoi456"},
        )
        assert lai.status_code == 200

    async def test_mat_khau_hien_tai_sai_bi_tu_choi(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        access = dang_nhap.json()["access_token"]

        phan_hoi = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "SaiRoi123", "new_password": "MatKhauMoi456"},
            headers={"Authorization": f"Bearer {access}"},
        )

        assert phan_hoi.status_code == 400

    async def test_doi_mat_khau_thu_hoi_moi_phien(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        access = dang_nhap.json()["access_token"]
        refresh = dang_nhap.json()["refresh_token"]

        await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": MAT_KHAU, "new_password": "MatKhauMoi456"},
            headers={"Authorization": f"Bearer {access}"},
        )

        lam_moi = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh}
        )
        assert lam_moi.status_code == 401
```

- [ ] **Step 4: Chạy test**

```bash
cd backend
mkdir -p src/modules/identity/presentation/routers
touch src/modules/identity/presentation/routers/__init__.py
uv run pytest tests/e2e/test_auth_api.py -v
```

Expected: `14 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/modules/identity/presentation backend/tests/e2e/test_auth_api.py
git commit -m "feat: add authentication endpoints"
```

---

## Task 18: Router người dùng và phòng ban

**Files:**
- Create: `backend/src/modules/identity/presentation/schemas/user_schemas.py`
- Create: `backend/src/modules/identity/presentation/schemas/department_schemas.py`
- Create: `backend/src/modules/identity/presentation/routers/user_router.py`
- Create: `backend/src/modules/identity/presentation/routers/department_router.py`
- Test: `backend/tests/e2e/test_user_api.py`

**Interfaces:**
- Consumes: use case quản trị (Task 14–15), dependency (Task 16).
- Produces: toàn bộ endpoint `/users`, `/departments`, `/audit-logs` theo mục 4 của spec.

**Ghi chú:** phần này lặp lại khuôn mẫu của Task 17 — schema, router gọi use case, test đầu-cuối kiểm tra phân quyền. Vì khuôn mẫu đã rõ, plan chỉ ghi đầy đủ router người dùng; router phòng ban và nhật ký làm theo đúng cách đó.

- [ ] **Step 1: Viết `schemas/user_schemas.py`**

```python
"""Schema cho các endpoint quản lý người dùng."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.modules.identity.domain.value_objects.role import Role


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    role: Role
    department_id: UUID | None = None
    password: str = Field(min_length=8, max_length=200)


class UpdateUserRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=30)


class ChangeRoleRequest(BaseModel):
    role: Role
    department_id: UUID | None = None


class AssignDepartmentRequest(BaseModel):
    department_id: UUID | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=200)
```

- [ ] **Step 2: Viết `routers/user_router.py`**

```python
"""Endpoint quản lý người dùng."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from src.modules.identity.application.use_cases.assign_user_to_department import (
    AssignUserToDepartment,
)
from src.modules.identity.application.use_cases.change_user_role import ChangeUserRole
from src.modules.identity.application.use_cases.create_user import CreateUser
from src.modules.identity.application.use_cases.deactivate_user import DeactivateUser
from src.modules.identity.application.use_cases.get_user import GetUser
from src.modules.identity.application.use_cases.list_users import ListUsers
from src.modules.identity.application.use_cases.reactivate_user import ReactivateUser
from src.modules.identity.application.use_cases.reset_user_password import (
    ResetUserPassword,
)
from src.modules.identity.application.use_cases.update_user import UpdateUser
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.identity.infrastructure.security.password_hasher import (
    BcryptPasswordHasher,
)
from src.modules.identity.presentation.dependencies import (
    CurrentUser,
    DbSession,
    get_password_hasher,
)
from src.modules.identity.presentation.schemas.auth_schemas import UserResponse
from src.modules.identity.presentation.schemas.common import PageResponse
from src.modules.identity.presentation.schemas.user_schemas import (
    AssignDepartmentRequest,
    ChangeRoleRequest,
    CreateUserRequest,
    ResetPasswordRequest,
    UpdateUserRequest,
)
from src.shared.infrastructure.clock import SystemClock

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=PageResponse[UserResponse])
async def danh_sach_nguoi_dung(
    nguoi_goi: CurrentUser,
    session: DbSession,
    department_id: UUID | None = None,
    role: Role | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[UserResponse]:
    """Liệt kê người dùng trong phạm vi quyền của người gọi."""
    trang = await ListUsers(SqlAlchemyUserRepository(session)).execute(
        requester=nguoi_goi,
        department_id=department_id,
        role=role,
        is_active=is_active,
        search=search,
        limit=limit,
        offset=offset,
    )
    return PageResponse(
        items=[UserResponse.from_entity(u) for u in trang.items],
        total=trang.total,
        limit=trang.limit,
        offset=trang.offset,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def tao_nguoi_dung(
    du_lieu: CreateUserRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
    hasher: Annotated[BcryptPasswordHasher, Depends(get_password_hasher)],
) -> UserResponse:
    """Tạo tài khoản mới. Chỉ quản trị viên."""
    use_case = CreateUser(
        user_repo=SqlAlchemyUserRepository(session),
        department_repo=SqlAlchemyDepartmentRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        hasher=hasher,
        clock=SystemClock(),
    )
    user = await use_case.execute(
        requester=nguoi_goi,
        email=du_lieu.email,
        full_name=du_lieu.full_name,
        role=du_lieu.role,
        department_id=du_lieu.department_id,
        password=du_lieu.password,
        phone=du_lieu.phone,
    )
    return UserResponse.from_entity(user)


@router.get("/{user_id}", response_model=UserResponse)
async def xem_nguoi_dung(
    user_id: UUID, nguoi_goi: CurrentUser, session: DbSession
) -> UserResponse:
    user = await GetUser(SqlAlchemyUserRepository(session)).execute(
        requester=nguoi_goi, user_id=user_id
    )
    return UserResponse.from_entity(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def sua_nguoi_dung(
    user_id: UUID,
    du_lieu: UpdateUserRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
) -> UserResponse:
    use_case = UpdateUser(
        user_repo=SqlAlchemyUserRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    user = await use_case.execute(
        requester=nguoi_goi,
        user_id=user_id,
        full_name=du_lieu.full_name,
        phone=du_lieu.phone,
    )
    return UserResponse.from_entity(user)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def vo_hieu_hoa(
    user_id: UUID, nguoi_goi: CurrentUser, session: DbSession
) -> UserResponse:
    use_case = DeactivateUser(
        user_repo=SqlAlchemyUserRepository(session),
        refresh_token_repo=SqlAlchemyRefreshTokenRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    return UserResponse.from_entity(
        await use_case.execute(requester=nguoi_goi, user_id=user_id)
    )


@router.post("/{user_id}/reactivate", response_model=UserResponse)
async def kich_hoat_lai(
    user_id: UUID, nguoi_goi: CurrentUser, session: DbSession
) -> UserResponse:
    use_case = ReactivateUser(
        user_repo=SqlAlchemyUserRepository(session),
        department_repo=SqlAlchemyDepartmentRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    return UserResponse.from_entity(
        await use_case.execute(requester=nguoi_goi, user_id=user_id)
    )


@router.patch("/{user_id}/role", response_model=UserResponse)
async def doi_vai_tro(
    user_id: UUID,
    du_lieu: ChangeRoleRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
) -> UserResponse:
    use_case = ChangeUserRole(
        user_repo=SqlAlchemyUserRepository(session),
        department_repo=SqlAlchemyDepartmentRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    return UserResponse.from_entity(
        await use_case.execute(
            requester=nguoi_goi,
            user_id=user_id,
            new_role=du_lieu.role,
            department_id=du_lieu.department_id,
        )
    )


@router.patch("/{user_id}/department", response_model=UserResponse)
async def chuyen_phong_ban(
    user_id: UUID,
    du_lieu: AssignDepartmentRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
) -> UserResponse:
    use_case = AssignUserToDepartment(
        user_repo=SqlAlchemyUserRepository(session),
        department_repo=SqlAlchemyDepartmentRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    return UserResponse.from_entity(
        await use_case.execute(
            requester=nguoi_goi, user_id=user_id, department_id=du_lieu.department_id
        )
    )


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def dat_lai_mat_khau(
    user_id: UUID,
    du_lieu: ResetPasswordRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
    hasher: Annotated[BcryptPasswordHasher, Depends(get_password_hasher)],
) -> Response:
    use_case = ResetUserPassword(
        user_repo=SqlAlchemyUserRepository(session),
        refresh_token_repo=SqlAlchemyRefreshTokenRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        hasher=hasher,
        clock=SystemClock(),
    )
    await use_case.execute(
        requester=nguoi_goi, user_id=user_id, new_password=du_lieu.new_password
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 3: Viết `schemas/department_schemas.py`**

```python
"""Schema cho các endpoint phòng ban."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.identity.domain.entities.department import Department


class CreateDepartmentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class UpdateDepartmentRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class DepartmentResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, phong: Department) -> "DepartmentResponse":
        return cls(
            id=phong.id,
            name=phong.name,
            description=phong.description,
            is_active=phong.is_active,
            created_at=phong.created_at,
            updated_at=phong.updated_at,
        )
```

- [ ] **Step 4: Viết `routers/department_router.py`**

```python
"""Endpoint quản lý phòng ban và tra cứu nhật ký."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from src.modules.identity.application.use_cases.create_department import (
    CreateDepartment,
)
from src.modules.identity.application.use_cases.deactivate_department import (
    DeactivateDepartment,
)
from src.modules.identity.application.use_cases.get_department import GetDepartment
from src.modules.identity.application.use_cases.list_audit_logs import ListAuditLogs
from src.modules.identity.application.use_cases.list_departments import ListDepartments
from src.modules.identity.application.use_cases.update_department import (
    UpdateDepartment,
)
from src.modules.identity.domain.entities.audit_log import AuditAction
from src.modules.identity.infrastructure.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.identity.presentation.dependencies import CurrentUser, DbSession
from src.modules.identity.presentation.schemas.common import PageResponse
from src.modules.identity.presentation.schemas.department_schemas import (
    CreateDepartmentRequest,
    DepartmentResponse,
    UpdateDepartmentRequest,
)
from src.shared.infrastructure.clock import SystemClock

router = APIRouter(tags=["departments"])


@router.get("/departments", response_model=PageResponse[DepartmentResponse])
async def danh_sach_phong_ban(
    nguoi_goi: CurrentUser,
    session: DbSession,
    is_active: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[DepartmentResponse]:
    trang = await ListDepartments(SqlAlchemyDepartmentRepository(session)).execute(
        requester=nguoi_goi, is_active=is_active, limit=limit, offset=offset
    )
    return PageResponse(
        items=[DepartmentResponse.from_entity(d) for d in trang.items],
        total=trang.total,
        limit=trang.limit,
        offset=trang.offset,
    )


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def tao_phong_ban(
    du_lieu: CreateDepartmentRequest, nguoi_goi: CurrentUser, session: DbSession
) -> DepartmentResponse:
    use_case = CreateDepartment(
        department_repo=SqlAlchemyDepartmentRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    phong = await use_case.execute(
        requester=nguoi_goi, name=du_lieu.name, description=du_lieu.description
    )
    return DepartmentResponse.from_entity(phong)


@router.get("/departments/{department_id}", response_model=DepartmentResponse)
async def xem_phong_ban(
    department_id: UUID, nguoi_goi: CurrentUser, session: DbSession
) -> DepartmentResponse:
    phong = await GetDepartment(SqlAlchemyDepartmentRepository(session)).execute(
        requester=nguoi_goi, department_id=department_id
    )
    return DepartmentResponse.from_entity(phong)


@router.patch("/departments/{department_id}", response_model=DepartmentResponse)
async def sua_phong_ban(
    department_id: UUID,
    du_lieu: UpdateDepartmentRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
) -> DepartmentResponse:
    use_case = UpdateDepartment(
        department_repo=SqlAlchemyDepartmentRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    phong = await use_case.execute(
        requester=nguoi_goi,
        department_id=department_id,
        name=du_lieu.name,
        description=du_lieu.description,
    )
    return DepartmentResponse.from_entity(phong)


@router.post(
    "/departments/{department_id}/deactivate", response_model=DepartmentResponse
)
async def vo_hieu_hoa_phong_ban(
    department_id: UUID, nguoi_goi: CurrentUser, session: DbSession
) -> DepartmentResponse:
    use_case = DeactivateDepartment(
        department_repo=SqlAlchemyDepartmentRepository(session),
        user_repo=SqlAlchemyUserRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    phong = await use_case.execute(requester=nguoi_goi, department_id=department_id)
    return DepartmentResponse.from_entity(phong)


@router.get("/audit-logs", tags=["audit"])
async def danh_sach_nhat_ky(
    nguoi_goi: CurrentUser,
    session: DbSession,
    actor_id: UUID | None = None,
    action: AuditAction | None = None,
    resource_type: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    """Tra cứu nhật ký hệ thống. Chỉ quản trị viên."""
    trang = await ListAuditLogs(SqlAlchemyAuditLogRepository(session)).execute(
        requester=nguoi_goi,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "id": str(e.id),
                "action": e.action.value,
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "changes": e.changes,
                "ip_address": e.ip_address,
                "created_at": e.created_at.isoformat(),
            }
            for e in trang.items
        ],
        "total": trang.total,
        "limit": trang.limit,
        "offset": trang.offset,
    }
```

- [ ] **Step 5: Viết test đầu-cuối kiểm tra phân quyền**

File `backend/tests/e2e/test_user_api.py`:

```python
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU = "MatKhauDung123"


async def _tao_admin(engine: AsyncEngine) -> None:
    from src.modules.identity.infrastructure.security.password_hasher import (
        BcryptPasswordHasher,
    )
    from src.shared.domain.identifiers import new_id

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, full_name, phone, role, "
                "department_id, is_active, must_change_password, last_login_at, "
                "created_at, updated_at) VALUES (:id, 'admin@congty.vn', :hash, "
                "'Quản trị viên', NULL, 'ADMIN', NULL, true, false, NULL, now(), now())"
            ),
            {"id": new_id(), "hash": BcryptPasswordHasher(rounds=4).hash(MAT_KHAU)},
        )


async def _token(client: AsyncClient, email: str, mat_khau: str = MAT_KHAU) -> str:
    phan_hoi = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": mat_khau}
    )
    assert phan_hoi.status_code == 200, phan_hoi.text
    return phan_hoi.json()["access_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestLuongThietLapBanDau:
    async def test_admin_tao_phong_ban_roi_tao_nhan_vien(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        """Luồng dựng hệ thống từ đầu — kịch bản quan trọng nhất của Foundation."""
        await _tao_admin(engine)
        token = await _token(client, "admin@congty.vn")

        phong = await client.post(
            "/api/v1/departments",
            json={"name": "Tư vấn sản phẩm A"},
            headers=_bearer(token),
        )
        assert phong.status_code == 201
        phong_id = phong.json()["id"]

        manager = await client.post(
            "/api/v1/users",
            json={
                "email": "quanly@congty.vn",
                "full_name": "Trần Quản Lý",
                "role": "MANAGER",
                "department_id": phong_id,
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )
        assert manager.status_code == 201

        staff = await client.post(
            "/api/v1/users",
            json={
                "email": "nhanvien@congty.vn",
                "full_name": "Lê Nhân Viên",
                "role": "STAFF",
                "department_id": phong_id,
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )
        assert staff.status_code == 201

    async def test_nhan_vien_moi_buoc_phai_doi_mat_khau(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(token)
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "moi@congty.vn",
                "full_name": "Nhân viên mới",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )

        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "moi@congty.vn", "password": "MatKhauTam123"},
        )

        assert dang_nhap.json()["must_change_password"] is True


class TestPhanQuyen:
    async def test_khong_tao_duoc_manager_thu_hai_trong_phong(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(token)
        )
        phong_id = phong.json()["id"]
        for i in range(1):
            await client.post(
                "/api/v1/users",
                json={
                    "email": f"m{i}@congty.vn",
                    "full_name": "Quản lý",
                    "role": "MANAGER",
                    "department_id": phong_id,
                    "password": "MatKhauTam123",
                },
                headers=_bearer(token),
            )

        thu_hai = await client.post(
            "/api/v1/users",
            json={
                "email": "m2@congty.vn",
                "full_name": "Quản lý 2",
                "role": "MANAGER",
                "department_id": phong_id,
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )

        assert thu_hai.status_code == 422
        assert thu_hai.json()["error"]["code"] == "DEPARTMENT_ALREADY_HAS_MANAGER"

    async def test_staff_khong_goi_duoc_endpoint_quan_tri(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        admin_token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(admin_token)
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "staff@congty.vn",
                "full_name": "Nhân viên",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(admin_token),
        )
        staff_token = await _token(client, "staff@congty.vn", "MatKhauTam123")

        phan_hoi = await client.post(
            "/api/v1/users",
            json={
                "email": "khac@congty.vn",
                "full_name": "Người khác",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(staff_token),
        )

        assert phan_hoi.status_code == 403

    async def test_manager_chi_thay_nhan_vien_phong_minh(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        admin_token = await _token(client, "admin@congty.vn")
        phong_a = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(admin_token)
        )
        phong_b = await client.post(
            "/api/v1/departments", json={"name": "Phòng B"}, headers=_bearer(admin_token)
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "ma@congty.vn",
                "full_name": "Quản lý A",
                "role": "MANAGER",
                "department_id": phong_a.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(admin_token),
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "sb@congty.vn",
                "full_name": "Nhân viên B",
                "role": "STAFF",
                "department_id": phong_b.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(admin_token),
        )
        manager_token = await _token(client, "ma@congty.vn", "MatKhauTam123")

        danh_sach = await client.get(
            "/api/v1/users", headers=_bearer(manager_token)
        )

        emails = {u["email"] for u in danh_sach.json()["items"]}
        assert "sb@congty.vn" not in emails

    async def test_staff_khong_xem_duoc_nhat_ky(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        admin_token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(admin_token)
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "staff@congty.vn",
                "full_name": "Nhân viên",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(admin_token),
        )
        staff_token = await _token(client, "staff@congty.vn", "MatKhauTam123")

        phan_hoi = await client.get("/api/v1/audit-logs", headers=_bearer(staff_token))

        assert phan_hoi.status_code == 403


class TestVongDoiTaiKhoan:
    async def test_vo_hieu_hoa_thi_khong_dang_nhap_duoc(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        admin_token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(admin_token)
        )
        tao = await client.post(
            "/api/v1/users",
            json={
                "email": "nghi@congty.vn",
                "full_name": "Sắp nghỉ",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(admin_token),
        )
        user_id = tao.json()["id"]

        await client.post(
            f"/api/v1/users/{user_id}/deactivate", headers=_bearer(admin_token)
        )

        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "nghi@congty.vn", "password": "MatKhauTam123"},
        )
        assert dang_nhap.status_code == 400
        assert dang_nhap.json()["error"]["code"] == "INACTIVE_ACCOUNT"

    async def test_khong_vo_hieu_hoa_duoc_admin_cuoi_cung(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        token = await _token(client, "admin@congty.vn")
        toi = await client.get("/api/v1/auth/me", headers=_bearer(token))

        phan_hoi = await client.post(
            f"/api/v1/users/{toi.json()['id']}/deactivate", headers=_bearer(token)
        )

        assert phan_hoi.status_code == 422
        assert (
            phan_hoi.json()["error"]["code"] == "LAST_ADMIN_CANNOT_BE_DEACTIVATED"
        )

    async def test_khong_dong_duoc_phong_ban_con_nhan_vien(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(token)
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "con@congty.vn",
                "full_name": "Còn làm",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )

        phan_hoi = await client.post(
            f"/api/v1/departments/{phong.json()['id']}/deactivate",
            headers=_bearer(token),
        )

        assert phan_hoi.status_code == 422
        assert phan_hoi.json()["error"]["code"] == "DEPARTMENT_HAS_ACTIVE_MEMBERS"


class TestNhatKyGhiNhanDayDu:
    async def test_moi_thao_tac_deu_de_lai_ban_ghi(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(token)
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "x@congty.vn",
                "full_name": "Người X",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )

        nhat_ky = await client.get("/api/v1/audit-logs", headers=_bearer(token))

        hanh_dong = {e["action"] for e in nhat_ky.json()["items"]}
        assert "department.created" in hanh_dong
        assert "user.created" in hanh_dong
        assert "auth.login_succeeded" in hanh_dong
```

- [ ] **Step 6: Thêm lại phần đăng ký router vào `src/main.py`**

Nếu đã tạm bỏ khối import router ở Task 16, thêm lại bây giờ (xem Task 16 Step 4).

- [ ] **Step 7: Chạy toàn bộ test**

```bash
cd backend
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
git add backend/src/modules/identity/presentation backend/src/main.py \
        backend/tests/e2e/test_user_api.py
git commit -m "feat: add user, department, and audit log endpoints"
```

---

## Tiếp theo

- [Phần 4d — Hoàn thiện](2026-07-21-omnichat-foundation-part4d-hardening.md) (Task 19–20)
