"""Ghép nối phụ thuộc cho tầng HTTP của inbox.

Ranh giới quan trọng: tầng này **không import identity** (import-linter cấm).
Người gọi được dựng thành ``InboxActor`` trung lập từ access token, qua một bộ
giải mã token do composition root (main.py) đặt sẵn ở ``app.state`` — inbox chỉ
đọc các thuộc tính user_id/role/department_id, không biết kiểu identity.
"""

from collections.abc import AsyncIterator
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.domain.ports import (
    IAttachmentStore,
    IChannelAdapterRegistry,
    ICredentialCipher,
    IRealtimeNotifier,
    IWorkforceDirectory,
)
from src.modules.inbox.infrastructure.attachments.signed_url import AttachmentUrlSigner
from src.shared.application.exceptions import AuthenticationError
from src.shared.infrastructure.clock import SystemClock
from src.shared.infrastructure.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


class _TokenPayload(Protocol):
    """Hình dạng tối thiểu của payload token mà inbox cần (duck-typing)."""

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


async def get_actor(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DbSession,
) -> InboxActor:
    """Dựng ``InboxActor`` từ access token.

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

    return InboxActor(
        user_id=agent.user_id,
        role=ActorRole(agent.role),
        department_id=agent.department_id,
    )


Actor = Annotated[InboxActor, Depends(get_actor)]


def get_cipher(request: Request) -> ICredentialCipher:
    return request.app.state.inbox_cipher  # type: ignore[no-any-return]


def get_registry(request: Request) -> IChannelAdapterRegistry:
    return request.app.state.inbox_adapter_registry  # type: ignore[no-any-return]


def get_attachment_store(request: Request) -> IAttachmentStore:
    return request.app.state.inbox_attachment_store  # type: ignore[no-any-return]


def get_url_signer(request: Request) -> AttachmentUrlSigner:
    """Bộ ký URL tệp đính kèm, dựng ở composition root."""
    return request.app.state.inbox_url_signer  # type: ignore[no-any-return]


def get_clock() -> SystemClock:
    return SystemClock()


def get_notifier(request: Request) -> IRealtimeNotifier:
    """Notifier realtime dùng chung, đặt ở app.state (WebSocketNotifier)."""
    return request.app.state.inbox_notifier  # type: ignore[no-any-return]


def get_directory_for(request: Request, session: AsyncSession) -> IWorkforceDirectory:
    """Dựng ``IWorkforceDirectory`` qua factory do composition root cấp.

    Presentation KHÔNG import implementation (nó chạm identity); chỉ gọi factory
    ở ``app.state`` và nhận về đối tượng theo port. Đây là chỗ giữ contract
    inbox.presentation ⊥ identity.
    """
    factory = request.app.state.inbox_directory_factory
    return factory(session)  # type: ignore[no-any-return]


def get_directory(request: Request, session: DbSession) -> IWorkforceDirectory:
    return get_directory_for(request, session)


Cipher = Annotated[ICredentialCipher, Depends(get_cipher)]
Registry = Annotated[IChannelAdapterRegistry, Depends(get_registry)]
AttachmentStore = Annotated[IAttachmentStore, Depends(get_attachment_store)]
UrlSigner = Annotated[AttachmentUrlSigner, Depends(get_url_signer)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
Clock = Annotated[SystemClock, Depends(get_clock)]
Directory = Annotated[IWorkforceDirectory, Depends(get_directory)]
Notifier = Annotated[IRealtimeNotifier, Depends(get_notifier)]
