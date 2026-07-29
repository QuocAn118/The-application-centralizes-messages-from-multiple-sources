"""Chuyển đổi giữa ORM model và domain entity của từ khoá."""

from src.modules.keyword.domain.entities.keyword import Keyword
from src.modules.keyword.infrastructure.models.keyword_model import KeywordModel


class KeywordMapper:
    """Cầu nối giữa bảng ``keywords`` và entity ``Keyword``."""

    @staticmethod
    def to_domain(model: KeywordModel) -> Keyword:
        return Keyword(
            id=model.id,
            department_id=model.department_id,
            text=model.text,
            normalized=model.normalized,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: Keyword) -> KeywordModel:
        return KeywordModel(
            id=entity.id,
            department_id=entity.department_id,
            text=entity.text,
            normalized=entity.normalized,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def update_model(model: KeywordModel, entity: Keyword) -> None:
        model.text = entity.text
        model.normalized = entity.normalized
        model.updated_at = entity.updated_at
