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
from src.shared.infrastructure.rate_limiter import InMemoryRateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])


def _lay_rate_limiter(request: Request) -> InMemoryRateLimiter:
    """Lấy bộ giới hạn dùng chung cho toàn ứng dụng.

    Đặt trong ``app.state`` để mọi request chia sẻ cùng một bộ đếm; tạo mới
    theo từng request sẽ khiến giới hạn không có tác dụng.
    """
    limiter: InMemoryRateLimiter = request.app.state.login_rate_limiter
    return limiter


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
    limiter = _lay_rate_limiter(request)
    ip = _dia_chi_goi(request)
    # Giới hạn theo cả email và địa chỉ IP: theo email để bảo vệ một tài khoản
    # cụ thể, theo IP để chặn việc dò hàng loạt tài khoản khác nhau.
    limiter.check(f"email:{du_lieu.email.lower()}")
    if ip:
        limiter.check(f"ip:{ip}")

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
        ip_address=ip,
        user_agent=request.headers.get("User-Agent"),
    )

    # Đăng nhập thành công thì xoá bộ đếm: người gõ nhầm vài lần rồi vào được
    # không nên bị phạt ở lần sau.
    limiter.reset(f"email:{du_lieu.email.lower()}")
    if ip:
        limiter.reset(f"ip:{ip}")

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
        transaction=session,
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
