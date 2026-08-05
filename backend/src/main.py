"""Điểm khởi tạo ứng dụng."""

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
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
from src.shared.infrastructure.clock import SystemClock
from src.shared.infrastructure.config import Settings, get_settings
from src.shared.infrastructure.database import create_engine_and_session_factory
from src.shared.infrastructure.event_loop import cau_hinh_event_loop
from src.shared.infrastructure.logging import cau_hinh_logging, request_id_var
from src.shared.infrastructure.rate_limiter import (
    InMemoryRateLimiter,
    RateLimitExceededError,
)

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
    (RateLimitExceededError, 429),
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

    # Khởi tạo ngay tại đây, không đợi ``lifespan``: bộ đếm phải tồn tại kể cả
    # khi ứng dụng được dựng mà không chạy lifespan (ví dụ trong test đầu-cuối).
    app.state.login_rate_limiter = InMemoryRateLimiter(
        max_attempts=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
        clock=SystemClock(),
    )

    # CORS cho frontend chạy ở origin khác (dev: localhost:3000). Không có phần
    # này, trình duyệt chặn ngay ở bước preflight và mọi lời gọi API từ trang web
    # đều hỏng, dù server hoàn toàn khoẻ.
    #
    # ``allow_credentials=True`` để trình duyệt gửi kèm thông tin xác thực; đi
    # cùng nó thì danh sách origin phải cụ thể, không được dùng "*".
    cac_origin = settings.danh_sach_cors_origin
    if cac_origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cac_origin,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            # Để client đọc được mã truy vết khi cần báo lỗi.
            expose_headers=["X-Request-ID"],
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
    async def xu_ly_loi_du_lieu(request: Request, exc: RequestValidationError) -> JSONResponse:
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
    async def xu_ly_loi_khong_luong_truoc(request: Request, exc: Exception) -> JSONResponse:
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
        return JSONResponse(status_code=200, content={"status": "ok", "database": "ok"})

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

    # Hook post-ingest: các module hạ nguồn (keyword #2, assignment #3) đăng ký
    # callable chạy sau khi webhook ingest xong một tin. Hook post-close: chạy sau
    # khi một hội thoại được đóng (assignment #3 kéo hàng đợi). Khởi tạo TRƯỚC
    # _wire_inbox để các router của inbox luôn thấy danh sách (rỗng nếu không ai
    # đăng ký). Thứ tự đăng ký post_ingest quan trọng: #2 (phân phòng) phải trước
    # #3 (tự gán) để #3 thấy phòng #2 vừa gán.
    app.state.post_ingest_hooks = []
    app.state.post_close_hooks = []
    app.state.post_reply_hooks = []

    _wire_inbox(app, settings)
    _wire_hrm(app, settings)
    _wire_keyword(app, settings)
    _wire_assignment(app, settings)
    _wire_analytics(app, settings)

    return app


def _wire_inbox(app: FastAPI, settings: Settings) -> None:
    """Ghép nối module inbox: adapter, cipher, store, notifier, router.

    Đặt riêng để composition root gọn; đây là chỗ *duy nhất* biết cả identity
    (token_service) lẫn hạ tầng inbox — hợp lệ vì main.py là composition root,
    không thuộc ``src.modules.inbox.presentation`` (contract chỉ cấm tầng đó).
    """
    from cryptography.fernet import Fernet

    from src.modules.identity.presentation.dependencies import get_token_service
    from src.modules.inbox.domain.value_objects.platform import Platform
    from src.modules.inbox.infrastructure.attachments.local_store import (
        LocalAttachmentStore,
    )
    from src.modules.inbox.infrastructure.channels.meta_adapter import MetaAdapter
    from src.modules.inbox.infrastructure.channels.registry import ChannelAdapterRegistry
    from src.modules.inbox.infrastructure.channels.zalo_adapter import ZaloAdapter
    from src.modules.inbox.infrastructure.directory.workforce_directory import (
        IdentityWorkforceDirectory,
    )
    from src.modules.inbox.infrastructure.realtime.ws_notifier import WebSocketNotifier
    from src.modules.inbox.infrastructure.security.fernet_cipher import (
        FernetCredentialCipher,
    )
    from src.modules.inbox.presentation.routers.channel_router import (
        router as channel_router,
    )
    from src.modules.inbox.presentation.routers.inbox_router import router as inbox_router
    from src.modules.inbox.presentation.routers.webhook_router import (
        router as webhook_router,
    )
    from src.modules.inbox.presentation.routers.ws_router import router as ws_router

    # Token service để inbox dựng InboxActor từ JWT mà không import identity.
    app.state.token_service = get_token_service(settings)

    cipher_key = settings.channel_cipher_key
    if not cipher_key:
        if settings.app_env != "development":
            # Production/staging: thiếu khoá là lỗi cấu hình nghiêm trọng — sinh
            # khoá tạm sẽ làm mất khả năng giải mã credential sau restart. Fail fast.
            raise RuntimeError(
                "CHANNEL_CIPHER_KEY bắt buộc khi app_env != development. "
                "Sinh khoá bằng Fernet.generate_key() và đặt vào .env."
            )
        # Dev: sinh khoá tạm để app chạy được, cảnh báo.
        cipher_key = Fernet.generate_key().decode()
        logger.warning(
            "CHANNEL_CIPHER_KEY chưa đặt — dùng khoá tạm; credential sẽ không giải "
            "mã lại được sau khi khởi động lại. Đặt khoá thật trước khi dùng thật."
        )
    app.state.inbox_cipher = FernetCredentialCipher(cipher_key)
    app.state.inbox_attachment_store = LocalAttachmentStore(settings.attachment_storage_dir)
    app.state.inbox_notifier = WebSocketNotifier()
    # Factory để inbox.presentation lấy IWorkforceDirectory mà không import
    # implementation (chỗ chạm identity) — giữ contract inbox.presentation ⊥ identity.
    app.state.inbox_directory_factory = IdentityWorkforceDirectory
    app.state.inbox_webhook_verify_token = settings.webhook_verify_token or None
    app.state.inbox_adapter_registry = ChannelAdapterRegistry(
        [
            ZaloAdapter(settings.zalo_app_id, settings.zalo_oa_secret_key),
            MetaAdapter(Platform.FACEBOOK, settings.meta_app_secret),
            MetaAdapter(Platform.INSTAGRAM, settings.meta_app_secret),
        ]
    )

    app.include_router(webhook_router, prefix="/api/v1")
    app.include_router(inbox_router, prefix="/api/v1")
    app.include_router(channel_router, prefix="/api/v1")
    app.include_router(ws_router)


def _wire_hrm(app: FastAPI, settings: Settings) -> None:
    """Ghép nối module hrm: token service, hai cầu nối qua factory, notifier, router.

    Đây là chỗ *duy nhất* biết cả identity (token_service, IdentityWorkforceDirectory)
    lẫn inbox (InboxPerformanceSource) cùng lúc — hợp lệ vì main.py là composition
    root, không thuộc ``src.modules.hrm.presentation`` (contract chỉ cấm tầng đó).
    Presentation chỉ nhận factory qua ``app.state`` và type theo port.
    """
    from src.modules.hrm.infrastructure.directory.workforce_directory import (
        IdentityWorkforceDirectory,
    )
    from src.modules.hrm.infrastructure.notifier.log_notifier import LogNotifier
    from src.modules.hrm.infrastructure.performance.inbox_performance_source import (
        InboxPerformanceSource,
    )
    from src.modules.hrm.presentation.routers.kpi_router import router as kpi_router
    from src.modules.hrm.presentation.routers.request_router import (
        router as request_router,
    )
    from src.modules.hrm.presentation.routers.shift_router import router as shift_router
    from src.modules.identity.presentation.dependencies import get_token_service

    # token_service có thể đã được _wire_inbox đặt; đặt lại vô hại (cùng giá trị).
    app.state.token_service = get_token_service(settings)
    # Factory để hrm.presentation lấy hai cầu nối mà không import implementation
    # (chỗ chạm identity/inbox) — giữ contract hrm.presentation ⊥ identity, inbox.
    app.state.hrm_directory_factory = IdentityWorkforceDirectory
    app.state.hrm_performance_factory = InboxPerformanceSource
    app.state.hrm_notifier = LogNotifier()

    app.include_router(shift_router, prefix="/api/v1")
    app.include_router(kpi_router, prefix="/api/v1")
    app.include_router(request_router, prefix="/api/v1")


def _wire_keyword(app: FastAPI, settings: Settings) -> None:
    """Ghép nối module keyword (#2): directory, adapter Claude, cầu nối, hook.

    Đây là composition root nên được biết cả identity, inbox lẫn Claude cùng lúc
    (contract chỉ cấm tầng keyword.presentation). Đặt các factory ở ``app.state``
    để presentation ráp use case mà không import implementation, và đăng ký hook
    post-ingest để tin mới kích hoạt phân tích — webhook router của inbox gọi hook
    qua ``app.state`` chứ không import keyword (giữ inbox ⊥ keyword).

    Không có ``ANTHROPIC_API_KEY`` (dev/test): dùng classifier "vô hiệu" luôn ném
    ``ClassifierError`` → mọi hội thoại rơi vào NOT_ANALYZED, luồng nhận tin vẫn
    chạy. Test bơm classifier giả qua ``app.state.keyword_classifier_factory``.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.modules.identity.presentation.dependencies import get_token_service
    from src.modules.keyword.application.use_cases.analyze_conversation import (
        AnalyzeConversation,
    )
    from src.modules.keyword.domain.ports import (
        ClassifierError,
        IConversationClassifier,
    )
    from src.modules.keyword.infrastructure.classifier.claude_classifier import (
        ClaudeConversationClassifier,
    )
    from src.modules.keyword.infrastructure.directory.workforce_directory import (
        IdentityWorkforceDirectory,
    )
    from src.modules.keyword.infrastructure.inbox_bridge.analyze_factory import (
        build_analyze_conversation,
    )
    from src.modules.keyword.infrastructure.inbox_bridge.conversation_directory import (
        InboxConversationDirectory,
    )
    from src.modules.keyword.infrastructure.inbox_bridge.conversation_router import (
        InboxConversationRouter,
    )
    from src.modules.keyword.infrastructure.inbox_bridge.post_ingest_hook import (
        make_post_ingest_hook,
    )
    from src.modules.keyword.presentation.routers.analysis_router import (
        router as analysis_router,
    )
    from src.modules.keyword.presentation.routers.keyword_router import (
        router as keyword_router,
    )

    app.state.token_service = get_token_service(settings)
    app.state.keyword_directory_factory = IdentityWorkforceDirectory
    app.state.keyword_conversation_directory_factory = InboxConversationDirectory

    # Router tự phân cần notifier realtime của inbox để phát tín hiệu khi đổi
    # trạng thái — dùng chung singleton _wire_inbox đã đặt. Clock hệ thống.
    notifier = app.state.inbox_notifier
    clock = SystemClock()

    def conversation_router_factory(session: AsyncSession) -> InboxConversationRouter:
        return InboxConversationRouter(session, notifier=notifier, clock=clock)

    app.state.keyword_conversation_router_factory = conversation_router_factory

    api_key = settings.anthropic_api_key
    if api_key:
        from anthropic import AsyncAnthropic

        anthropic_client = AsyncAnthropic(api_key=api_key)

        def classifier_factory() -> IConversationClassifier:
            return ClaudeConversationClassifier(anthropic_client, settings.anthropic_model)
    else:
        logger.warning(
            "ANTHROPIC_API_KEY chưa đặt — phân tích #2 vô hiệu (mọi hội thoại "
            "NOT_ANALYZED). Đặt khoá thật trong .env để bật tự phân bằng LLM."
        )

        class _DisabledClassifier:
            async def classify(self, texts, departments):  # type: ignore[no-untyped-def]
                raise ClassifierError("Chưa cấu hình ANTHROPIC_API_KEY.")

        def classifier_factory() -> IConversationClassifier:
            return _DisabledClassifier()

    app.state.keyword_classifier_factory = classifier_factory

    # Hook post-ingest: mỗi tin mới (không trùng) kích hoạt phân tích trên session
    # riêng, sau khi #1 đã commit. Ráp cùng builder mà endpoint force dùng. Đọc
    # classifier factory LƯỜI từ app.state để test bơm classifier giả sau khi dựng
    # app vẫn có hiệu lực (giống lối presentation lấy factory ở request-time).
    def analyze_factory(session: AsyncSession) -> AnalyzeConversation:
        return build_analyze_conversation(
            session,
            classifier_factory=app.state.keyword_classifier_factory,
            conversation_directory_factory=InboxConversationDirectory,
            conversation_router_factory=conversation_router_factory,
            workforce_factory=IdentityWorkforceDirectory,
            clock=clock,
        )

    app.state.post_ingest_hooks.append(
        make_post_ingest_hook(lambda: app.state.session_factory, analyze_factory)
    )

    app.include_router(keyword_router, prefix="/api/v1")
    app.include_router(analysis_router, prefix="/api/v1")


def _wire_assignment(app: FastAPI, settings: Settings) -> None:
    """Ghép nối module assignment (#3): directory actor, factory kéo hàng đợi, hai hook.

    Composition root nên được biết cả identity (directory dựng actor), inbox lẫn
    hrm cùng lúc (contract chỉ cấm tầng assignment.presentation). Đặt các factory ở
    ``app.state`` để presentation ráp use case mà không import implementation.

    Hai trigger tự động — nối qua ``app.state`` để #1/#2 KHÔNG import #3:
    - ``post_ingest`` (#3): SAU hook #2 (đăng ký sau nên chạy sau), nếu hội thoại
      vừa được #2 phân phòng (DANG_MO + có phòng + chưa ai nhận) → tự gán nhân viên.
    - ``post_close`` (#3): khi nhân viên đóng hội thoại → kéo hàng đợi phòng đó.

    NỢ F1 (review GĐ3): pool so "đang trong ca" theo giờ nghiệp vụ địa phương — PHẢI
    truyền ``settings.app_timezone`` vào mọi builder pool ở đây.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.modules.assignment.application.use_cases.auto_assign_conversation import (
        AutoAssignConversation,
    )
    from src.modules.assignment.application.use_cases.pull_department_queue import (
        PullDepartmentQueue,
    )
    from src.modules.assignment.infrastructure.inbox_bridge.post_close_hook import (
        make_post_close_hook,
    )
    from src.modules.assignment.infrastructure.inbox_bridge.post_ingest_hook import (
        make_post_ingest_hook,
    )
    from src.modules.assignment.infrastructure.inbox_bridge.pull_queue_factory import (
        build_auto_assign_conversation,
        build_pull_department_queue,
    )
    from src.modules.assignment.presentation.routers.assignment_router import (
        router as assignment_router,
    )
    from src.modules.identity.presentation.dependencies import get_token_service
    from src.modules.inbox.infrastructure.directory.workforce_directory import (
        IdentityWorkforceDirectory,
    )

    app.state.token_service = get_token_service(settings)
    # Directory (identity) để assignment.presentation dựng AssignmentActor mà không
    # import implementation — lấy qua factory ở app.state (giống inbox/keyword).
    app.state.assignment_directory_factory = IdentityWorkforceDirectory

    # Notifier realtime dùng chung của inbox (đổi trạng thái khi tự gán phát tín
    # hiệu đúng) và clock hệ thống. Timezone lấy từ config (nợ F1).
    notifier = app.state.inbox_notifier
    clock = SystemClock()
    timezone = settings.app_timezone

    def pull_queue_factory(session: AsyncSession) -> PullDepartmentQueue:
        return build_pull_department_queue(
            session, notifier=notifier, clock=clock, timezone=timezone
        )

    def auto_assign_factory(session: AsyncSession) -> AutoAssignConversation:
        return build_auto_assign_conversation(
            session, notifier=notifier, clock=clock, timezone=timezone
        )

    # Endpoint kéo hàng đợi thủ công dùng chung builder pull-queue.
    app.state.assignment_pull_queue_factory = pull_queue_factory

    # Trigger tự gán sau ingest: đăng ký SAU hook #2 để chạy sau nó (thấy phòng #2
    # vừa gán). Cả hai hook chạy trên session riêng, đọc factory lười ở app.state.
    app.state.post_ingest_hooks.append(
        make_post_ingest_hook(lambda: app.state.session_factory, auto_assign_factory)
    )
    # Trigger kéo hàng đợi sau khi đóng hội thoại.
    app.state.post_close_hooks.append(
        make_post_close_hook(lambda: app.state.session_factory, pull_queue_factory)
    )

    app.include_router(assignment_router, prefix="/api/v1")


def _wire_analytics(app: FastAPI, settings: Settings) -> None:
    """Ghép nối module analytics (#5): directory actor, factory use case, 3 hook.

    Composition root nên được biết identity (directory dựng actor), inbox (nguồn +
    hook) và hrm (nguồn) cùng lúc (contract chỉ cấm tầng analytics.presentation).
    Đặt factory ở ``app.state`` để presentation ráp use case mà không import
    implementation.

    Ba trigger incremental — nối qua ``app.state`` để #1 KHÔNG import #5:
    - ``post_ingest`` (tin khách) → +1 inbound. Đăng ký SAU #2/#3 để thấy phòng đã
      phân (đọc ``conversation.department_id`` HIỆN TẠI — nợ F-A review GĐ3).
    - ``post_reply`` (nhân viên trả lời) → +1 outbound + mẫu first_response (tin đầu).
    - ``post_close`` (đóng hội thoại) → +1 closed/handled + mẫu resolution.

    ``assigned_count`` dựng từ ``assignment_log`` (#3) qua backfill — không hook
    incremental (chốt: log là nguồn sự thật, rebuild định kỳ cập nhật "hôm nay").
    Timezone (``app_timezone``) truyền vào mọi hook + source (event-time, nợ F1 #3).
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.modules.analytics.application.use_cases.apply_event_delta import (
        ApplyEventDelta,
    )
    from src.modules.analytics.application.use_cases.rebuild_daily_rollup import (
        RebuildDailyRollup,
    )
    from src.modules.analytics.infrastructure.hooks.rollup_hooks import (
        make_post_close_hook,
        make_post_ingest_hook,
        make_post_reply_hook,
    )
    from src.modules.analytics.infrastructure.repositories.rollup_repository import (
        SqlAlchemyRollupRepository,
    )
    from src.modules.analytics.infrastructure.sources.hrm_stats_source import (
        HrmStatsSource,
    )
    from src.modules.analytics.infrastructure.sources.inbox_stats_source import (
        InboxStatsSource,
    )
    from src.modules.analytics.presentation.routers.analytics_router import (
        router as analytics_router,
    )
    from src.modules.identity.presentation.dependencies import get_token_service
    from src.modules.inbox.infrastructure.directory.workforce_directory import (
        IdentityWorkforceDirectory,
    )

    app.state.token_service = get_token_service(settings)
    app.state.analytics_directory_factory = IdentityWorkforceDirectory
    app.state.analytics_rollup_repo_factory = SqlAlchemyRollupRepository
    app.state.analytics_hrm_source_factory = HrmStatsSource

    tz = settings.app_timezone

    def rebuild_factory(session: AsyncSession) -> RebuildDailyRollup:
        return RebuildDailyRollup(
            InboxStatsSource(session, tz), SqlAlchemyRollupRepository(session)
        )

    app.state.analytics_rebuild_factory = rebuild_factory

    def apply_factory(session: AsyncSession) -> ApplyEventDelta:
        return ApplyEventDelta(SqlAlchemyRollupRepository(session))

    provider = lambda: app.state.session_factory  # noqa: E731
    # post_ingest #5 đăng ký SAU #2 (phân tích) + #3 (tự gán) để thấy phòng đã phân.
    app.state.post_ingest_hooks.append(make_post_ingest_hook(provider, apply_factory, tz))
    app.state.post_reply_hooks.append(make_post_reply_hook(provider, apply_factory, tz))
    app.state.post_close_hooks.append(make_post_close_hook(provider, apply_factory, tz))

    app.include_router(analytics_router, prefix="/api/v1")


app = create_app()
