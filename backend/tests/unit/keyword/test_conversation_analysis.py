from datetime import UTC, datetime
from decimal import Decimal

from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)
from src.modules.keyword.domain.value_objects.extracted_term import (
    AnalysisOutcome,
    ExtractedTerm,
)
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)


def _terms() -> tuple[ExtractedTerm, ...]:
    return (ExtractedTerm(text="Bảo hành", normalized="bao hanh"),)


class TestConversationAnalysis:
    def test_auto_assigned(self) -> None:
        ht, phong = new_id(), new_id()
        a = ConversationAnalysis.auto_assigned(
            conversation_id=ht,
            extracted_terms=_terms(),
            department_id=phong,
            confidence=Decimal("0.9"),
            now=BAY_GIO,
        )

        assert a.outcome is AnalysisOutcome.AUTO_ASSIGNED
        assert a.suggested_department_id == phong
        assert a.confidence == Decimal("0.9")
        assert len(a.extracted_terms) == 1

    def test_ambiguous_giu_terms_khong_co_phong(self) -> None:
        ht = new_id()
        a = ConversationAnalysis.ambiguous(
            conversation_id=ht,
            extracted_terms=_terms(),
            confidence=Decimal("0.4"),
            now=BAY_GIO,
        )

        assert a.outcome is AnalysisOutcome.AMBIGUOUS
        assert a.suggested_department_id is None
        # Vẫn lưu cụm nhu cầu để #5 phát hiện nhu cầu mới.
        assert len(a.extracted_terms) == 1

    def test_not_analyzed_rong(self) -> None:
        ht = new_id()
        a = ConversationAnalysis.not_analyzed(conversation_id=ht, now=BAY_GIO)

        assert a.outcome is AnalysisOutcome.NOT_ANALYZED
        assert a.suggested_department_id is None
        assert a.confidence is None
        assert a.extracted_terms == ()
