"""ORM model cho bảng bản ghi phân tích hội thoại."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class ConversationAnalysisModel(Base):
    """Bảng ``conversation_analyses``.

    Một hội thoại có thể có nhiều bản ghi (phân tích lại nhiều lần) → giữ lịch sử
    cho #5. ``conversation_id`` và ``suggested_department_id`` là UUID thuần tham
    chiếu inbox/identity, không khoá ngoại (giữ module độc lập).

    ``terms`` lưu JSONB danh sách cụm nhu cầu LLM trích, mỗi phần tử là
    ``{"text": ..., "normalized": ...}`` — giữ nguyên kể cả khi không phân được
    phòng, để #5 phát hiện nhu cầu mới. ``suggested_department_id``/``confidence``
    chỉ có khi tự phân (AUTO_ASSIGNED) hoặc mơ hồ (AMBIGUOUS có confidence).

    Lưu ý ``confidence`` là ``Numeric(4, 3)``: giá trị được **làm tròn về 3 chữ
    số thập phân** khi lưu (ví dụ 0.87654 → 0.877). Việc *gác* tự phân so sánh
    confidence với ngưỡng ở use case xảy ra TRƯỚC khi lưu, trên giá trị đầy đủ
    của LLM, nên không bị ảnh hưởng; nhưng #3/#5 khi đọc lại chỉ thấy giá trị đã
    làm tròn — đừng giả định độ chính xác tuyệt đối.
    """

    __tablename__ = "conversation_analyses"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    terms: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False)
    suggested_department_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_conversation_analysis_conversation_id", "conversation_id"),
        Index("ix_conversation_analysis_suggested_department_id", "suggested_department_id"),
    )
