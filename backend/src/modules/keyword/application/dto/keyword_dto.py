"""DTO đọc cho tầng application của keyword — thuần dữ liệu, bất biến."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.modules.keyword.domain.value_objects.extracted_term import AnalysisOutcome


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class KeywordView:
    id: UUID
    department_id: UUID
    text: str
    normalized: str


@dataclass(frozen=True)
class ExtractedTermView:
    text: str
    normalized: str


@dataclass(frozen=True)
class AnalysisView:
    id: UUID
    conversation_id: UUID
    outcome: AnalysisOutcome
    extracted_terms: tuple[ExtractedTermView, ...]
    created_at: datetime
    suggested_department_id: UUID | None = None
    confidence: Decimal | None = None
