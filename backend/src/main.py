"""Điểm khởi tạo ứng dụng."""

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
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
from src.shared.infrastructure.event_loop import cau_hinh_event_loop
from src.shared.infrastructure.logging import cau_hinh_logging, request_id_var

# Uvicorn không tự chọn event loop tương thích với psycopg trên Windows, nên
# phải cấu hình ngay khi module được nạp — trước khi uvicorn dựng loop.
cau_hinh_event_loop()

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
                    "details": {"cac_loi": jsonable_encoder(exc.errors())},
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
