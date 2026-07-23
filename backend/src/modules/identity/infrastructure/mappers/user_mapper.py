"""Chuyển đổi giữa ORM model và domain entity của người dùng."""

from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.models.user_model import UserModel


class UserMapper:
    """Cầu nối giữa bảng ``users`` và entity ``User``.

    Value object được tháo ra thành chuỗi khi ghi và dựng lại khi đọc.
    """

    @staticmethod
    def to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            email=Email(model.email),
            password_hash=PasswordHash(model.password_hash),
            full_name=model.full_name,
            phone=model.phone,
            role=Role(model.role),
            department_id=model.department_id,
            is_active=model.is_active,
            must_change_password=model.must_change_password,
            last_login_at=model.last_login_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: User) -> UserModel:
        return UserModel(
            id=entity.id,
            email=entity.email.value,
            password_hash=entity.password_hash.value,
            full_name=entity.full_name,
            phone=entity.phone,
            role=entity.role.value,
            department_id=entity.department_id,
            is_active=entity.is_active,
            must_change_password=entity.must_change_password,
            last_login_at=entity.last_login_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def update_model(model: UserModel, entity: User) -> None:
        model.email = entity.email.value
        model.password_hash = entity.password_hash.value
        model.full_name = entity.full_name
        model.phone = entity.phone
        model.role = entity.role.value
        model.department_id = entity.department_id
        model.is_active = entity.is_active
        model.must_change_password = entity.must_change_password
        model.last_login_at = entity.last_login_at
        model.updated_at = entity.updated_at
