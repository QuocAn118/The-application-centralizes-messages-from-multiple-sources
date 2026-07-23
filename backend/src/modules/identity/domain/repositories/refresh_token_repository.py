"""Interface repository cho refresh token."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.entities.refresh_token import RefreshToken


class IRefreshTokenRepository(Protocol):
    """Truy xuất và lưu trữ refresh token."""

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    async def add(self, token: RefreshToken) -> None: ...

    async def update(self, token: RefreshToken) -> None: ...

    async def revoke_all_for_user(self, user_id: UUID, now: datetime) -> None:
        """Thu hồi mọi token còn hiệu lực của một người dùng.

        Dùng khi vô hiệu hoá tài khoản hoặc khi đổi mật khẩu.
        """
        ...

    async def revoke_chain(self, token: RefreshToken, now: datetime) -> None:
        """Thu hồi toàn bộ chuỗi token nối với ``token`` qua ``replaced_by_id``.

        Dùng khi phát hiện một token đã bị thay thế lại được gửi lên — dấu hiệu
        token đã bị đánh cắp.
        """
        ...
