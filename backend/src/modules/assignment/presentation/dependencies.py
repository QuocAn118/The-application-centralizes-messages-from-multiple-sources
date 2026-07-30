"""Ghép nối phụ thuộc cho tầng HTTP của assignment.

Ranh giới quan trọng: tầng này **không import inbox/hrm/identity** (import-linter
cấm). Người gọi được dựng thành ``AssignmentActor`` trung lập từ access token, qua
một bộ giải mã token do composition root (main.py) đặt sẵn ở ``app.state``. Việc
kiểm nhân viên còn hoạt động + đọc vai/phòng lấy qua một *directory factory* ở
``app.state`` (không import implementation — chỗ chạm identity). ``PullDepartmentQueue``
cũng dựng qua factory ở ``app.state``, ráp trong ``assignment.infrastructure``.
"""

from collections.abc import AsyncIterator
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.assignment.application.actor import ActorRole, AssignmentActor
from src.modules.assignment.application.use_cases.pull_department_queue import (
    PullDepartmentQueue,
)
from src.shared.application.exceptions import AuthenticationError

_bearer = HTTPBearer(auto_error=False)


class _TokenPayload(Protocol):
    """Hình dạng tối thiểu của payload token mà assignment cần (duck-typing)."""

    user_id: UUID


class _TokenDecoder(Protocol):
    def decode_access_token(self, token: str) -> _TokenPayload: ...


class _AgentInfo(Protocol):
    """Hình dạng tối thiểu của kết quả ``get_agent`` từ directory identity."""

    user_id: UUID
    department_id: UUID | None
    role: str
    is_active: bool


class _WorkforceDirectory(Protocol):
    async def get_agent(self, user_id: UUID) -> _AgentInfo | None: ...


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Mở một session cho mỗi request; commit khi xong, rollback nếu lỗi."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_session)]


async def get_actor(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DbSession,
) -> AssignmentActor:
    """Dựng ``AssignmentActor`` từ access token.

    Kiểm nhân viên còn hoạt động qua directory (factory ở ``app.state``) — tài
    khoản vừa bị vô hiệu hoá mất quyền ngay ở request kế tiếp dù token còn hạn.
    """
    if credentials is None:
        raise AuthenticationError("Thiếu thông tin xác thực.", code="MISSING_CREDENTIALS")

    decoder: _TokenDecoder = request.app.state.token_service
    payload = decoder.decode_access_token(credentials.credentials)

    directory: _WorkforceDirectory = request.app.state.assignment_directory_factory(session)
    agent = await directory.get_agent(payload.user_id)
    if agent is None or not agent.is_active:
        raise AuthenticationError("Tài khoản không còn hiệu lực.", code="INACTIVE_ACCOUNT")

    return AssignmentActor(
        user_id=agent.user_id,
        role=ActorRole(agent.role),
        department_id=agent.department_id,
    )


Actor = Annotated[AssignmentActor, Depends(get_actor)]


def build_pull_department_queue(request: Request, session: AsyncSession) -> PullDepartmentQueue:
    """Dựng ``PullDepartmentQueue`` qua factory ở ``app.state``.

    Factory (do composition root cấp) ráp pool/hàng đợi/assigner trong
    ``assignment.infrastructure`` và đã đóng sẵn ``notifier``, ``clock`` và
    ``timezone`` (= ``settings.app_timezone``) — presentation không import
    implementation, giữ contract assignment.presentation ⊥ inbox/hrm/identity.
    """
    factory = request.app.state.assignment_pull_queue_factory
    return factory(session)  # type: ignore[no-any-return]
