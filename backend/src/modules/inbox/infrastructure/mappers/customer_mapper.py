"""Chuyển đổi giữa ORM model và domain entity của khách hàng."""

from src.modules.inbox.domain.entities.customer import Customer
from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.models.customer_model import CustomerModel


class CustomerMapper:
    """Cầu nối giữa bảng ``customers`` và entity ``Customer``."""

    @staticmethod
    def to_domain(model: CustomerModel) -> Customer:
        return Customer(
            id=model.id,
            channel_id=model.channel_id,
            platform=Platform(model.platform),
            external_id=model.external_id,
            display_name=model.display_name,
            avatar_url=model.avatar_url,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: Customer) -> CustomerModel:
        return CustomerModel(
            id=entity.id,
            channel_id=entity.channel_id,
            platform=entity.platform.value,
            external_id=entity.external_id,
            display_name=entity.display_name,
            avatar_url=entity.avatar_url,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def update_model(model: CustomerModel, entity: Customer) -> None:
        model.display_name = entity.display_name
        model.avatar_url = entity.avatar_url
        model.updated_at = entity.updated_at
