"""Repository người dùng dùng SQLAlchemy."""

from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.mappers.user_mapper import UserMapper
from src.modules.identity.infrastructure.models.user_model import UserModel

_SelectT = TypeVar("_SelectT", bound=Select[Any])

class SqlAlchemyUserRepository:
    """Truy xuất người dùng từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lay_model(self, user_id: UUID) -> UserModel | None:
        ket_qua = await self._session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return ket_qua.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._lay_model(user_id)
        return UserMapper.to_domain(model) if model else None

    async def get_by_email(self, email: Email) -> User | None:
        ket_qua = await self._session.execute(
            select(UserModel).where(func.lower(UserModel.email) == email.value)
        )
        model = ket_qua.scalar_one_or_none()
        return UserMapper.to_domain(model) if model else None

    async def add(self, user: User) -> None:
        self._session.add(UserMapper.to_model(user))

    async def update(self, user: User) -> None:
        """Ghi thay đổi lên bản ghi đang có.

        Phải đọc model ra trước rồi sửa, thay vì tạo model mới — nếu không
        SQLAlchemy sẽ coi đó là một bản ghi khác và cố chèn thêm.
        """
        model = await self._lay_model(user.id)
        if model is None:
            raise ValueError(f"Không tìm thấy người dùng {user.id} để cập nhật.")
        UserMapper.update_model(model, user)

    def _ap_dung_bo_loc(
        self,
        cau_truy_van: _SelectT,
        department_id: UUID | None,
        role: Role | None,
        is_active: bool | None,
        search: str | None,
    ) -> _SelectT:
        if department_id is not None:
            cau_truy_van = cau_truy_van.where(UserModel.department_id == department_id)
        if role is not None:
            cau_truy_van = cau_truy_van.where(UserModel.role == role.value)
        if is_active is not None:
            cau_truy_van = cau_truy_van.where(UserModel.is_active == is_active)
        if search:
            mau = f"%{search.lower()}%"
            cau_truy_van = cau_truy_van.where(
                func.lower(UserModel.full_name).like(mau)
                | func.lower(UserModel.email).like(mau)
            )
        return cau_truy_van

    async def list_users(
        self,
        department_id: UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        cau_truy_van = self._ap_dung_bo_loc(
            select(UserModel), department_id, role, is_active, search
        )
        cau_truy_van = cau_truy_van.order_by(UserModel.created_at).limit(limit).offset(offset)
        ket_qua = await self._session.execute(cau_truy_van)
        return [UserMapper.to_domain(m) for m in ket_qua.scalars()]

    async def count_users(
        self,
        department_id: UUID | None = None,
        role: Role | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> int:
        cau_truy_van = self._ap_dung_bo_loc(
            select(func.count()).select_from(UserModel),
            department_id,
            role,
            is_active,
            search,
        )
        ket_qua = await self._session.execute(cau_truy_van)
        return int(ket_qua.scalar_one())

    async def count_active_in_department(self, department_id: UUID) -> int:
        ket_qua = await self._session.execute(
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.department_id == department_id, UserModel.is_active)
        )
        return int(ket_qua.scalar_one())

    async def has_active_manager(
        self, department_id: UUID, exclude_user_id: UUID | None = None
    ) -> bool:
        cau_truy_van = (
            select(func.count())
            .select_from(UserModel)
            .where(
                UserModel.department_id == department_id,
                UserModel.role == Role.MANAGER.value,
                UserModel.is_active,
            )
        )
        if exclude_user_id is not None:
            cau_truy_van = cau_truy_van.where(UserModel.id != exclude_user_id)
        ket_qua = await self._session.execute(cau_truy_van)
        return int(ket_qua.scalar_one()) > 0

    async def count_active_admins(self) -> int:
        ket_qua = await self._session.execute(
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.role == Role.ADMIN.value, UserModel.is_active)
        )
        return int(ket_qua.scalar_one())
