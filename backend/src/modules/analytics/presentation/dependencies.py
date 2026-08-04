"""Ghép nối phụ thuộc cho tầng HTTP của analytics.

Ranh giới: tầng này **không import inbox/hrm/identity** (import-linter cấm). Actor
dựng từ JWT qua ``token_service`` + directory factory ở ``app.state``. Các use case
đọc-rollup và đọc-thẳng-#4 dựng qua factory ở ``app.state`` (ráp ở
``analytics.infrastructure``) — presentation không chạm implementation.
"""

from collections.abc import AsyncIterator
from datetime import date
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.analytics.application.actor import ActorRole, AnalyticsActor
from src.modules.analytics.application.use_cases.get_reports import (
    GetAgentReport,
    GetConversationReport,
    GetRequestReport,
    GetWorkforceReport,
)
from src.modules.analytics.application.use_cases.rebuild_daily_rollup import (
    RebuildDailyRollup,
)
from src.modules.analytics.domain.value_objects.metrics import DateRange
from src.shared.application.exceptions import AuthenticationError

_bearer = HTTPBearer(auto_error=False)


class _TokenPayload(Protocol):
    user_id: UUID


class _TokenDecoder(Protocol):
    def decode_access_token(self, token: str) -> _TokenPayload: ...


class _AgentInfo(Protocol):
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
) -> AnalyticsActor:
    """Dựng ``AnalyticsActor`` từ access token; kiểm tài khoản còn hoạt động."""
    if credentials is None:
        raise AuthenticationError("Thiếu thông tin xác thực.", code="MISSING_CREDENTIALS")

    decoder: _TokenDecoder = request.app.state.token_service
    payload = decoder.decode_access_token(credentials.credentials)

    directory: _WorkforceDirectory = request.app.state.analytics_directory_factory(session)
    agent = await directory.get_agent(payload.user_id)
    if agent is None or not agent.is_active:
        raise AuthenticationError("Tài khoản không còn hiệu lực.", code="INACTIVE_ACCOUNT")

    return AnalyticsActor(
        user_id=agent.user_id,
        role=ActorRole(agent.role),
        department_id=agent.department_id,
    )


Actor = Annotated[AnalyticsActor, Depends(get_actor)]


def get_date_range(
    from_: Annotated[date, Query(alias="from")],
    to: Annotated[date, Query()],
) -> DateRange:
    """Khoảng ngày báo cáo từ query ``from``/``to`` (đóng hai đầu; from ≤ to)."""
    return DateRange(from_date=from_, to_date=to)


DateRangeParam = Annotated[DateRange, Depends(get_date_range)]


# ----- Factory dựng use case (ráp ở analytics.infrastructure qua app.state) -----


def get_conversation_report(request: Request, session: AsyncSession) -> GetConversationReport:
    return GetConversationReport(request.app.state.analytics_rollup_repo_factory(session))


def get_agent_report(request: Request, session: AsyncSession) -> GetAgentReport:
    return GetAgentReport(request.app.state.analytics_rollup_repo_factory(session))


def get_workforce_report(request: Request, session: AsyncSession) -> GetWorkforceReport:
    return GetWorkforceReport(request.app.state.analytics_hrm_source_factory(session))


def get_request_report(request: Request, session: AsyncSession) -> GetRequestReport:
    return GetRequestReport(request.app.state.analytics_hrm_source_factory(session))


def get_rebuild(request: Request, session: AsyncSession) -> RebuildDailyRollup:
    return request.app.state.analytics_rebuild_factory(session)  # type: ignore[no-any-return]
