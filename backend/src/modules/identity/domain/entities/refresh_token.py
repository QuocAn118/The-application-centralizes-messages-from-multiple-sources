"""Entity refresh token."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.shared.domain.entity import AggregateRoot


@dataclass(eq=False, kw_only=True)
class RefreshToken(AggregateRoot):
    """Một refresh token đã cấp cho người dùng.

    Chỉ lưu hash của token, không lưu token thô — kẻ đọc được cơ sở dữ liệu
    vẫn không mạo danh được người dùng.

    ``replaced_by_id`` tạo thành chuỗi token nối tiếp nhau. Khi một token đã
    bị thay thế lại được gửi lên, hệ thống hiểu là token bị đánh cắp và thu hồi
    toàn bộ chuỗi.
    """

    user_id: UUID
    token_hash: str
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None = None
    replaced_by_id: UUID | None = None
    user_agent: str | None = None
    ip_address: str | None = None

    @classmethod
    def issue(
        cls,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> "RefreshToken":
        return cls(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
            replaced_by_id=None,
            user_agent=user_agent,
            ip_address=ip_address,
            created_at=now,
        )

    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def is_valid(self, now: datetime) -> bool:
        return not self.is_revoked() and not self.is_expired(now)

    def revoke(self, now: datetime) -> None:
        """Thu hồi token. Gọi lại lần nữa không làm thay đổi mốc thu hồi ban đầu."""
        if self.revoked_at is None:
            self.revoked_at = now

    def rotate_to(self, new_token_id: UUID, now: datetime) -> None:
        """Thu hồi token này và ghi nhận token thay thế nó."""
        self.revoke(now)
        self.replaced_by_id = new_token_id
