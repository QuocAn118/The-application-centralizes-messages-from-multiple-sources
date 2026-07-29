"""Schema Pydantic cho các endpoint keyword.

Chỉ mô tả dữ liệu vào/ra HTTP; nghiệp vụ nằm ở use case. Các ``*Response`` dựng
từ DTO của tầng application để router không lộ entity domain ra ngoài.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.keyword.application.dto.keyword_dto import (
    AnalysisView,
    KeywordView,
    Page,
)
from src.modules.keyword.domain.value_objects.extracted_term import AnalysisOutcome

# ----- Keyword -----


class CreateKeywordRequest(BaseModel):
    department_id: UUID
    text: str = Field(min_length=1, max_length=200)


class UpdateKeywordRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200)


class KeywordResponse(BaseModel):
    id: UUID
    department_id: UUID
    text: str
    normalized: str

    @classmethod
    def from_view(cls, v: KeywordView) -> "KeywordResponse":
        return cls(id=v.id, department_id=v.department_id, text=v.text, normalized=v.normalized)


# ----- Analysis -----


class ExtractedTermResponse(BaseModel):
    text: str
    normalized: str


class AnalysisResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    outcome: AnalysisOutcome
    extracted_terms: list[ExtractedTermResponse]
    created_at: datetime
    suggested_department_id: UUID | None = None
    confidence: Decimal | None = None

    @classmethod
    def from_view(cls, v: AnalysisView) -> "AnalysisResponse":
        return cls(
            id=v.id,
            conversation_id=v.conversation_id,
            outcome=v.outcome,
            extracted_terms=[
                ExtractedTermResponse(text=t.text, normalized=t.normalized)
                for t in v.extracted_terms
            ],
            created_at=v.created_at,
            suggested_department_id=v.suggested_department_id,
            confidence=v.confidence,
        )


class AnalysisPageResponse(BaseModel):
    items: list[AnalysisResponse]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_page(cls, page: Page[AnalysisView]) -> "AnalysisPageResponse":
        return cls(
            items=[AnalysisResponse.from_view(v) for v in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )
