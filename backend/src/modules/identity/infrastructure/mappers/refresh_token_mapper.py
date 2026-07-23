"""Chuyển đổi giữa ORM model và domain entity của refresh token."""

from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.infrastructure.models.refresh_token_model import (
    RefreshTokenModel,
)


class RefreshTokenMapper:
    """Cầu nối giữa bảng ``refresh_tokens`` và entity ``RefreshToken``."""

    @staticmethod
    def to_domain(model: RefreshTokenModel) -> RefreshToken:
        return RefreshToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
            replaced_by_id=model.replaced_by_id,
            user_agent=model.user_agent,
            ip_address=model.ip_address,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: RefreshToken) -> RefreshTokenModel:
        return RefreshTokenModel(
            id=entity.id,
            user_id=entity.user_id,
            token_hash=entity.token_hash,
            expires_at=entity.expires_at,
            revoked_at=entity.revoked_at,
            replaced_by_id=entity.replaced_by_id,
            user_agent=entity.user_agent,
            ip_address=entity.ip_address,
            created_at=entity.created_at,
        )

    @staticmethod
    def update_model(model: RefreshTokenModel, entity: RefreshToken) -> None:
        model.revoked_at = entity.revoked_at
        model.replaced_by_id = entity.replaced_by_id
