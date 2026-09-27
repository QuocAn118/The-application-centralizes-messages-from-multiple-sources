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
