"""Chuyển đổi giữa ORM model và domain entity của bản ghi phân tích."""

from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)
from src.modules.keyword.domain.value_objects.extracted_term import (
    AnalysisOutcome,
    ExtractedTerm,
)
from src.modules.keyword.infrastructure.models.conversation_analysis_model import (
    ConversationAnalysisModel,
)


class ConversationAnalysisMapper:
    """Cầu nối giữa bảng ``conversation_analyses`` và entity ``ConversationAnalysis``.

    Danh sách ``ExtractedTerm`` được tuần tự hoá thành JSONB (mỗi phần tử
    ``{"text": ..., "normalized": ...}``) khi lưu và dựng lại khi đọc. Bản ghi
    không sửa sau khi tạo nên không cần ``update_model``.
    """

    @staticmethod
    def to_domain(model: ConversationAnalysisModel) -> ConversationAnalysis:
        return ConversationAnalysis(
            id=model.id,
            conversation_id=model.conversation_id,
            outcome=AnalysisOutcome(model.outcome),
            extracted_terms=tuple(
                ExtractedTerm(text=t["text"], normalized=t["normalized"]) for t in model.terms
            ),
            suggested_department_id=model.suggested_department_id,
            confidence=model.confidence,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: ConversationAnalysis) -> ConversationAnalysisModel:
        return ConversationAnalysisModel(
            id=entity.id,
            conversation_id=entity.conversation_id,
            outcome=entity.outcome.value,
            terms=[{"text": t.text, "normalized": t.normalized} for t in entity.extracted_terms],
            suggested_department_id=entity.suggested_department_id,
            confidence=entity.confidence,
            created_at=entity.created_at,
        )
