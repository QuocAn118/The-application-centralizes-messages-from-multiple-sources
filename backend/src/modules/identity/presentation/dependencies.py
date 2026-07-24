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
