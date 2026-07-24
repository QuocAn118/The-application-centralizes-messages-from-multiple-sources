"""Schema cho các endpoint quản lý người dùng."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.modules.identity.domain.value_objects.role import Role


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    role: Role
    department_id: UUID | None = None
    password: str = Field(min_length=8, max_length=200)


class UpdateUserRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=30)


class ChangeRoleRequest(BaseModel):
    role: Role
    department_id: UUID | None = None


class AssignDepartmentRequest(BaseModel):
    department_id: UUID | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=200)
