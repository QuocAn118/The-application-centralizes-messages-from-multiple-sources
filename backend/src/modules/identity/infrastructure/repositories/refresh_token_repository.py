"""Repository refresh token dùng SQLAlchemy."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.refresh_token import RefreshToken
from src.modules.identity.infrastructure.mappers.refresh_token_mapper import (
    RefreshTokenMapper,
)
from src.modules.identity.infrastructure.models.refresh_token_model import (
    RefreshTokenModel,
)


class SqlAlchemyRefreshTokenRepository:
    """Truy xuất refresh token từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        ket_qua = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        model = ket_qua.scalar_one_or_none()
        return RefreshTokenMapper.to_domain(model) if model else None

    async def add(self, token: RefreshToken) -> None:
        self._session.add(RefreshTokenMapper.to_model(token))

    async def update(self, token: RefreshToken) -> None:
        ket_qua = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.id == token.id)
        )
        model = ket_qua.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Không tìm thấy refresh token {token.id} để cập nhật.")
        RefreshTokenMapper.update_model(model, token)

    async def revoke_all_for_user(self, user_id: UUID, now: datetime) -> None:
        """Thu hồi mọi token chưa bị thu hồi của người dùng bằng một câu lệnh."""
        await self._session.execute(
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

    async def revoke_chain(self, token: RefreshToken, now: datetime) -> None:
        """Thu hồi toàn bộ chuỗi token nối tiếp nhau.

        Duyệt theo ``replaced_by_id``. Có tập ``da_duyet`` để dừng nếu dữ liệu
        bị hỏng tạo thành vòng lặp.
        """
        ma_hien_tai: UUID | None = token.id
        da_duyet: set[UUID] = set()

        while ma_hien_tai is not None and ma_hien_tai not in da_duyet:
            da_duyet.add(ma_hien_tai)
            ket_qua = await self._session.execute(
                select(RefreshTokenModel).where(RefreshTokenModel.id == ma_hien_tai)
            )
            model = ket_qua.scalar_one_or_none()
            if model is None:
                break
            if model.revoked_at is None:
                model.revoked_at = now
            ma_hien_tai = model.replaced_by_id
