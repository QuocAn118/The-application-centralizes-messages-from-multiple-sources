"""Entity bản ghi phân tích một hội thoại bằng LLM."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.modules.keyword.domain.value_objects.extracted_term import (
    AnalysisOutcome,
    ExtractedTerm,
)
from src.shared.domain.entity import AggregateRoot


@dataclass(eq=False, kw_only=True)
class ConversationAnalysis(AggregateRoot):
    """Kết quả một lần phân tích nhu cầu của một hội thoại.

    Một hội thoại có thể phân tích lại nhiều lần (ví dụ có thêm tin) → nhiều bản
    ghi; giữ lịch sử cho #5 báo cáo nhu cầu. ``conversation_id`` và
    ``suggested_department_id`` là UUID thuần tham chiếu inbox/identity, không
    khoá ngoại.

    ``outcome`` cho biết kết cục: đã tự phân, mơ hồ (giữ CHO_PHAN), hay không
    phân tích được (LLM lỗi/chưa đủ tin). ``suggested_department_id`` chỉ có khi
    ``AUTO_ASSIGNED``; ``extracted_terms`` giữ mọi cụm nhu cầu LLM trả (kể cả khi
    không khớp phòng nào) để #5 phát hiện nhu cầu mới.
    """

    conversation_id: UUID
    outcome: AnalysisOutcome
    extracted_terms: tuple[ExtractedTerm, ...]
    created_at: datetime
    suggested_department_id: UUID | None = None
    confidence: Decimal | None = None

    @classmethod
    def auto_assigned(
        cls,
        conversation_id: UUID,
        extracted_terms: tuple[ExtractedTerm, ...],
        department_id: UUID,
        confidence: Decimal,
        now: datetime,
    ) -> "ConversationAnalysis":
        """Đã khớp đúng một phòng đủ tin cậy và tự phân về phòng đó."""
        return cls(
            conversation_id=conversation_id,
            outcome=AnalysisOutcome.AUTO_ASSIGNED,
            extracted_terms=extracted_terms,
            suggested_department_id=department_id,
            confidence=confidence,
            created_at=now,
        )

    @classmethod
    def ambiguous(
        cls,
        conversation_id: UUID,
        extracted_terms: tuple[ExtractedTerm, ...],
        confidence: Decimal,
        now: datetime,
    ) -> "ConversationAnalysis":
        """Trích được nhu cầu nhưng không suy ra một phòng rõ ràng → giữ CHO_PHAN."""
        return cls(
            conversation_id=conversation_id,
            outcome=AnalysisOutcome.AMBIGUOUS,
            extracted_terms=extracted_terms,
            confidence=confidence,
            created_at=now,
        )

    @classmethod
    def not_analyzed(cls, conversation_id: UUID, now: datetime) -> "ConversationAnalysis":
        """Không phân tích được (LLM lỗi hoặc chưa đủ tin) — không trích được gì."""
        return cls(
            conversation_id=conversation_id,
            outcome=AnalysisOutcome.NOT_ANALYZED,
            extracted_terms=(),
            created_at=now,
        )
