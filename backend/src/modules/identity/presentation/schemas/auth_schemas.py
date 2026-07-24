"""Schema cho các endpoint xác thực."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.modules.identity.domain.entities.user import User


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int = Field(description="Số giây còn lại của access token")
    must_change_password: bool = Field(
        default=False,
        description="Nếu đúng, client phải chuyển sang màn hình đổi mật khẩu",
    )


class UserResponse(BaseModel):
    """Thông tin người dùng trả về cho client.

    Cố ý không có ``password_hash`` — dùng schema riêng thay vì trả thẳng
    entity là cách chắc chắn nhất để dữ liệu nhạy cảm không lọt ra ngoài.
    """

    id: UUID
    email: str
    full_name: str
    phone: str | None
    role: str
    department_id: UUID | None
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email.value,
            full_name=user.full_name,
            phone=user.phone,
            role=user.role.value,
            department_id=user.department_id,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )
