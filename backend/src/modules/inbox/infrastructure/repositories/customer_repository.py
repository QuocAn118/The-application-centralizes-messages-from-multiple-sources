"""Repository khách hàng dùng SQLAlchemy."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.infrastructure.mappers.customer_mapper import CustomerMapper
from src.modules.inbox.infrastructure.models.customer_model import CustomerModel


class SqlAlchemyCustomerRepository:
    """Truy xuất khách hàng từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lay_model(self, customer_id: UUID) -> CustomerModel | None:
        ket_qua = await self._session.execute(
            select(CustomerModel).where(CustomerModel.id == customer_id)
        )
        return ket_qua.scalar_one_or_none()

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        model = await self._lay_model(customer_id)
        return CustomerMapper.to_domain(model) if model else None

    async def get_by_external(self, channel_id: UUID, external_id: str) -> Customer | None:
        ket_qua = await self._session.execute(
            select(CustomerModel).where(
                CustomerModel.channel_id == channel_id,
                CustomerModel.external_id == external_id,
            )
        )
        model = ket_qua.scalar_one_or_none()
        return CustomerMapper.to_domain(model) if model else None

    async def add(self, customer: Customer) -> None:
        self._session.add(CustomerMapper.to_model(customer))

    async def update(self, customer: Customer) -> None:
        model = await self._lay_model(customer.id)
        if model is None:
            raise ValueError(f"Không tìm thấy khách {customer.id} để cập nhật.")
        CustomerMapper.update_model(model, customer)
