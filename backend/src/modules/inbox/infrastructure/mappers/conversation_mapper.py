"""Chuyển đổi giữa ORM model và domain entity của hội thoại."""

from src.modules.inbox.domain.entities.conversation import (
    Conversation,
    ConversationStatus,
)
from src.modules.inbox.infrastructure.models.conversation_model import ConversationModel


class ConversationMapper:
    """Cầu nối giữa bảng ``conversations`` và entity ``Conversation``."""

    @staticmethod
    def to_domain(model: ConversationModel) -> Conversation:
        return Conversation(
            id=model.id,
            channel_id=model.channel_id,
            customer_id=model.customer_id,
            status=ConversationStatus(model.status),
            department_id=model.department_id,
            assigned_user_id=model.assigned_user_id,
            last_message_at=model.last_message_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: Conversation) -> ConversationModel:
        return ConversationModel(
            id=entity.id,
            channel_id=entity.channel_id,
            customer_id=entity.customer_id,
            status=entity.status.value,
            department_id=entity.department_id,
            assigned_user_id=entity.assigned_user_id,
            last_message_at=entity.last_message_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def update_model(model: ConversationModel, entity: Conversation) -> None:
        model.status = entity.status.value
        model.department_id = entity.department_id
        model.assigned_user_id = entity.assigned_user_id
        model.last_message_at = entity.last_message_at
        model.updated_at = entity.updated_at
