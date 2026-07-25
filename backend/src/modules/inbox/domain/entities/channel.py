"""Entity kênh — một tài khoản kết nối trên một nền tảng."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.inbox.domain.value_objects.platform import Platform
from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import BusinessRuleViolationError


class EmptyExternalChannelIdError(BusinessRuleViolationError):
    """Mã kênh do nền tảng cấp không được rỗng."""

    def __init__(self) -> None:
        super().__init__(
            "Mã kênh trên nền tảng không được để trống.",
            code="EMPTY_EXTERNAL_CHANNEL_ID",
        )


@dataclass(eq=False, kw_only=True)
class Channel(AggregateRoot):
    """Một kênh kết nối: một Zalo OA, một Facebook Page, hoặc một Instagram.

    ``department_id`` là tham chiếu UUID sang phòng ban của module identity —
    cố ý không phải khoá ngoại, để module inbox độc lập với identity. Kênh
    chưa gắn phòng thì hội thoại đến từ nó rơi vào mục chờ-phân.

    ``encrypted_credential`` là token đã mã hoá; entity không bao giờ giữ token
    thô. Việc mã hoá/giải mã do use case làm qua một cổng riêng.
    """

    platform: Platform
    external_channel_id: str
    name: str
    encrypted_credential: str
    created_at: datetime
    updated_at: datetime
    department_id: UUID | None = None
    is_active: bool = True

    @staticmethod
    def _chuan_hoa_ma(external_channel_id: str) -> str:
        ma = external_channel_id.strip()
        if not ma:
            raise EmptyExternalChannelIdError
        return ma

    @classmethod
    def connect(
        cls,
        platform: Platform,
        external_channel_id: str,
        name: str,
        department_id: UUID | None,
        encrypted_credential: str,
        now: datetime,
    ) -> "Channel":
        """Kết nối một kênh mới."""
        return cls(
            platform=platform,
            external_channel_id=cls._chuan_hoa_ma(external_channel_id),
            name=name.strip(),
            department_id=department_id,
            encrypted_credential=encrypted_credential,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    def assign_department(self, department_id: UUID | None, now: datetime) -> None:
        self.department_id = department_id
        self.updated_at = now

    def update_credential(self, encrypted_credential: str, now: datetime) -> None:
        self.encrypted_credential = encrypted_credential
        self.updated_at = now

    def rename(self, name: str, now: datetime) -> None:
        self.name = name.strip()
        self.updated_at = now

    def deactivate(self, now: datetime) -> None:
        self.is_active = False
        self.updated_at = now
