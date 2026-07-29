"""Ghép nối phụ thuộc cho tầng HTTP của keyword.

Ranh giới quan trọng: tầng này **không import identity lẫn inbox** (import-linter
cấm). Người gọi được dựng thành ``KeywordActor`` trung lập từ access token, qua
một bộ giải mã token do composition root (main.py) đặt sẵn ở ``app.state``. Cầu
nối sang identity — ``IWorkforceDirectory`` — cũng lấy qua factory ở
``app.state``, không import implementation.
"""

from collections.abc import AsyncIterator
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.keyword.application.actor import ActorRole, KeywordActor
from src.modules.keyword.application.use_cases.analyze_conversation import (
    AnalyzeConversation,
)
from src.modules.keyword.domain.ports import IWorkforceDirectory
from src.modules.keyword.infrastructure.inbox_bridge.analyze_factory import (
    build_analyze_conversation as _build_analyze_conversation,
)
from src.shared.application.exceptions import AuthenticationError
from src.shared.infrastructure.clock import SystemClock

_bearer = HTTPBearer(auto_error=False)


class _TokenPayload(Protocol):
    """Hình dạng tối thiểu của payload token mà keyword cần (duck-typing)."""

    user_id: UUID
    department_id: UUID | None

    @property
    def role(self) -> object: ...


class _TokenDecoder(Protocol):
    def decode_access_token(self, token: str) -> _TokenPayload: ...


class _AgentInfo(Protocol):
    """Hình dạng tối thiểu của kết quả ``IWorkforceDirectory.get_agent``."""

    user_id: UUID
    department_id: UUID | None
    role: str
    is_active: bool


class _WorkforceDirectory(Protocol):
    """Directory keyword dùng để dựng actor — cần cả ``get_agent``.

    Port miền ``IWorkforceDirectory`` chỉ khai báo ``department_exists_active``
    (đủ cho use case). Ở đây cần thêm ``get_agent`` để đọc quyền người gọi; adapter
    ``IdentityWorkforceDirectory`` có sẵn cả hai, nên chỉ nới kiểu tại tầng này.
    """

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


def get_directory_for(request: Request, session: AsyncSession) -> IWorkforceDirectory:
    """Dựng ``IWorkforceDirectory`` qua factory do composition root cấp.

    Presentation KHÔNG import implementation (nó chạm identity); chỉ gọi factory
    ở ``app.state``. Đây là chỗ giữ contract keyword.presentation ⊥ identity.
    """
    factory = request.app.state.keyword_directory_factory
    return factory(session)  # type: ignore[no-any-return]


async def get_actor(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DbSession,
) -> KeywordActor:
    """Dựng ``KeywordActor`` từ access token.

    Kiểm nhân viên còn hoạt động qua directory — tài khoản vừa bị vô hiệu hoá mất
    quyền ngay ở request kế tiếp dù token còn hạn.
    """
    if credentials is None:
        raise AuthenticationError("Thiếu thông tin xác thực.", code="MISSING_CREDENTIALS")

    decoder: _TokenDecoder = request.app.state.token_service
    payload = decoder.decode_access_token(credentials.credentials)

    directory: _WorkforceDirectory = request.app.state.keyword_directory_factory(session)
    agent = await directory.get_agent(payload.user_id)
    if agent is None or not agent.is_active:
        raise AuthenticationError("Tài khoản không còn hiệu lực.", code="INACTIVE_ACCOUNT")

    return KeywordActor(
        user_id=agent.user_id,
        role=ActorRole(agent.role),
        department_id=agent.department_id,
    )


Actor = Annotated[KeywordActor, Depends(get_actor)]


def get_clock() -> SystemClock:
    return SystemClock()


def get_directory(request: Request, session: DbSession) -> IWorkforceDirectory:
    return get_directory_for(request, session)


Clock = Annotated[SystemClock, Depends(get_clock)]
Directory = Annotated[IWorkforceDirectory, Depends(get_directory)]


def build_analyze_conversation(request: Request, session: AsyncSession) -> AnalyzeConversation:
    """Dựng ``AnalyzeConversation`` từ các factory ở ``app.state``.

    Mọi cầu nối chạm inbox/identity/Claude lấy qua factory (composition root cấp),
    ráp trong ``keyword.infrastructure`` — presentation không import implementation,
    giữ contract keyword.presentation ⊥ identity, inbox. Dùng cho endpoint kích
    hoạt lại (force); hook post-ingest ráp cùng builder với các factory tương tự.
    """
    state = request.app.state
    return _build_analyze_conversation(
        session,
        classifier_factory=state.keyword_classifier_factory,
        conversation_directory_factory=state.keyword_conversation_directory_factory,
        conversation_router_factory=state.keyword_conversation_router_factory,
        workforce_factory=state.keyword_directory_factory,
        clock=SystemClock(),
    )
