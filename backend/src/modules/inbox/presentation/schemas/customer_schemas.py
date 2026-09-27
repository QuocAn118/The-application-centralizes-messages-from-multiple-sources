"""Schema cho panel khách (2b): ghi chú (BE-5)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.inbox.application.use_cases.customer_notes import NoteView
from src.modules.inbox.domain.entities.customer_note import DAI_TOI_DA


class NoteRequest(BaseModel):
    body: str = Field(min_length=1, max_length=DAI_TOI_DA)


class NoteResponse(BaseModel):
    id: UUID
    customer_id: UUID
    # ``null`` = ghi chú của quản trị viên (chỉ Admin thấy).
    department_id: UUID | None
    department_name: str | None
    author_id: UUID
    author_name: str | None
    body: str
    created_at: datetime

    @classmethod
    def from_view(cls, v: NoteView) -> "NoteResponse":
        return cls(**v.__dict__)


class TagResponse(BaseModel):
    id: UUID
    name: str
    color: str
    is_active: bool


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    # Chỉ swatch-1..8 — kiểm ở domain (TAG_COLOR_INVALID, 422).
    color: str


class TagUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = None
    is_active: bool | None = None


class CustomerTagsRequest(BaseModel):
    tag_ids: list[UUID] = Field(max_length=50)


class TemplateResponse(BaseModel):
    id: UUID
    # ``null`` = mẫu dùng chung mọi phòng.
    department_id: UUID | None
    title: str
    body: str
    updated_at: datetime


class TemplateCreateRequest(BaseModel):
    department_id: UUID | None = None
    title: str = Field(min_length=1, max_length=80)
    body: str = Field(min_length=1, max_length=4000)


class TemplateUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    body: str | None = Field(default=None, min_length=1, max_length=4000)
