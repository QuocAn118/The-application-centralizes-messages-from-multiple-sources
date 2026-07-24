"""Schema cho các endpoint phòng ban."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.identity.domain.entities.department import Department


class CreateDepartmentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class UpdateDepartmentRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class DepartmentResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, phong: Department) -> "DepartmentResponse":
        return cls(
            id=phong.id,
            name=phong.name,
            description=phong.description,
            is_active=phong.is_active,
            created_at=phong.created_at,
            updated_at=phong.updated_at,
        )
