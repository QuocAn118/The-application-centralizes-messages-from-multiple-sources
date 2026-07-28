"""Ghép nối phụ thuộc cho tầng HTTP của hrm.

Ranh giới quan trọng: tầng này **không import identity lẫn inbox** (import-linter
cấm). Người gọi được dựng thành ``HrmActor`` trung lập từ access token, qua một
bộ giải mã token do composition root (main.py) đặt sẵn ở ``app.state``. Hai cầu
nối sang module khác — ``IWorkforceDirectory`` (identity) và ``IPerformanceSource``
(inbox) — cũng lấy qua factory ở ``app.state``, không import implementation.
"""

from collections.abc import AsyncIterator
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.hrm.application.actor import ActorRole, HrmActor
from src.modules.hrm.domain.ports import INotifier, IPerformanceSource, IWorkforceDirectory
from src.shared.application.exceptions import AuthenticationError
from src.shared.infrastructure.clock import SystemClock

_bearer = HTTPBearer(auto_error=False)


class _TokenPayload(Protocol):
    """Hình dạng tối thiểu của payload token mà hrm cần (duck-typing)."""

    user_id: UUID
    department_id: UUID | None

    @property
    def role(self) -> object: ...


class _TokenDecoder(Protocol):
    def decode_access_token(self, token: str) -> _TokenPayload: ...


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


def get_directory_for(request: Request, session: AsyncSession) -> IWorkforceDirectory:
    """Dựng ``IWorkforceDirectory`` qua factory do composition root cấp.

    Presentation KHÔNG import implementation (nó chạm identity); chỉ gọi factory
    ở ``app.state`` và nhận về đối tượng theo port. Đây là chỗ giữ contract
    hrm.presentation ⊥ identity.
    """
    factory = request.app.state.hrm_directory_factory
    return factory(session)  # type: ignore[no-any-return]


def get_performance_for(request: Request, session: AsyncSession) -> IPerformanceSource:
    """Dựng ``IPerformanceSource`` qua factory — chỗ giữ contract hrm.presentation ⊥ inbox."""
    factory = request.app.state.hrm_performance_factory
    return factory(session)  # type: ignore[no-any-return]


async def get_actor(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DbSession,
) -> HrmActor:
    """Dựng ``HrmActor`` từ access token.

    Kiểm nhân viên còn hoạt động qua ``IWorkforceDirectory`` — tài khoản vừa bị
    vô hiệu hoá mất quyền ngay ở request kế tiếp dù token còn hạn.
    """
    if credentials is None:
        raise AuthenticationError("Thiếu thông tin xác thực.", code="MISSING_CREDENTIALS")

    decoder: _TokenDecoder = request.app.state.token_service
    payload = decoder.decode_access_token(credentials.credentials)

    directory = get_directory_for(request, session)
    agent = await directory.get_agent(payload.user_id)
    if agent is None or not agent.is_active:
        raise AuthenticationError("Tài khoản không còn hiệu lực.", code="INACTIVE_ACCOUNT")

    return HrmActor(
        user_id=agent.user_id,
        role=ActorRole(agent.role),
        department_id=agent.department_id,
    )


Actor = Annotated[HrmActor, Depends(get_actor)]


def get_clock() -> SystemClock:
    return SystemClock()


def get_directory(request: Request, session: DbSession) -> IWorkforceDirectory:
    return get_directory_for(request, session)


def get_performance(request: Request, session: DbSession) -> IPerformanceSource:
    return get_performance_for(request, session)


def get_notifier(request: Request) -> INotifier:
    """Notifier dùng chung, đặt ở app.state ở composition root."""
    return request.app.state.hrm_notifier  # type: ignore[no-any-return]


Clock = Annotated[SystemClock, Depends(get_clock)]
Directory = Annotated[IWorkforceDirectory, Depends(get_directory)]
Performance = Annotated[IPerformanceSource, Depends(get_performance)]
Notifier = Annotated[INotifier, Depends(get_notifier)]
