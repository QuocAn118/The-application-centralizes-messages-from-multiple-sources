"""Interface repository cho Customer."""

from typing import Protocol
from uuid import UUID

from src.modules.inbox.domain.entities.customer import Customer


class ICustomerRepository(Protocol):
    """Truy xuất khách hàng."""

    async def get_by_id(self, customer_id: UUID) -> Customer | None: ...

    async def get_by_external(self, channel_id: UUID, external_id: str) -> Customer | None:
        """Tra khách theo (kênh + mã nền tảng) — webhook dùng để tìm/tạo khách."""
        ...

    async def add(self, customer: Customer) -> None: ...

    async def update(self, customer: Customer) -> None: ...
