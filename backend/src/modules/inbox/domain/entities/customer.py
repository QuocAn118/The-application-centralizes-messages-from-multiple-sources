"""Entity khách hàng — người nhắn tin đến một kênh."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.inbox.domain.value_objects.platform import Platform
from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import BusinessRuleViolationError


class EmptyExternalIdError(BusinessRuleViolationError):
    """Mã khách do nền tảng cấp không được rỗng."""

    def __init__(self) -> None:
        super().__init__(
            "Mã khách trên nền tảng không được để trống.",
            code="EMPTY_EXTERNAL_ID",
        )


@dataclass(eq=False, kw_only=True)
class Customer(AggregateRoot):
    """Một người nhắn tin, định danh bởi (kênh + mã nền tảng cấp).

    Mỗi kênh giữ hồ sơ khách riêng: cùng một người nhắn Zalo và Facebook là
    hai ``Customer`` khác nhau. Gộp danh tính đa kênh không thuộc phạm vi #1.

    Webhook nhiều khi không kèm tên hay ảnh đại diện, nên ``display_name`` và
    ``avatar_url`` để rỗng được và cập nhật sau khi biết.
    """

    channel_id: UUID
    platform: Platform
    external_id: str
    created_at: datetime
    updated_at: datetime
    display_name: str | None = None
    avatar_url: str | None = None

    @staticmethod
    def _chuan_hoa_ma(external_id: str) -> str:
        ma = external_id.strip()
        if not ma:
            raise EmptyExternalIdError
        return ma

    @classmethod
    def register(
        cls,
        channel_id: UUID,
        platform: Platform,
        external_id: str,
        display_name: str | None,
        now: datetime,
        avatar_url: str | None = None,
    ) -> "Customer":
        """Ghi nhận một khách mới trên một kênh."""
        return cls(
            channel_id=channel_id,
            platform=platform,
            external_id=cls._chuan_hoa_ma(external_id),
            display_name=display_name,
            avatar_url=avatar_url,
            created_at=now,
            updated_at=now,
        )

    def update_profile(
        self, display_name: str | None, avatar_url: str | None, now: datetime
    ) -> None:
        """Cập nhật hồ sơ khi biết thêm thông tin. ``None`` nghĩa là giữ nguyên."""
        if display_name is not None:
            self.display_name = display_name
        if avatar_url is not None:
            self.avatar_url = avatar_url
        self.updated_at = now
