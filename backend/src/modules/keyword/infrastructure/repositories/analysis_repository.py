"""Repository bản ghi phân tích hội thoại dùng SQLAlchemy."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Select, column, func, or_, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)
from src.modules.keyword.domain.value_objects.extracted_term import AnalysisOutcome
from src.modules.keyword.infrastructure.mappers.conversation_analysis_mapper import (
    ConversationAnalysisMapper,
)
from src.modules.keyword.infrastructure.models.conversation_analysis_model import (
    ConversationAnalysisModel,
)

# Bảng hội thoại của inbox, tham chiếu bằng TÊN (không import model inbox): hợp đồng
# import-linter cấm keyword.presentation chạm inbox kể cả gián tiếp qua repo này.
# Chỉ đọc hai cột để biết hội thoại nào đang chờ phân (department_id NULL).
_HOI_THOAI = table("conversations", column("id"), column("department_id"))


class SqlAlchemyAnalysisRepository:
    """Truy xuất bản ghi phân tích hội thoại từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, analysis_id: UUID) -> ConversationAnalysis | None:
        ket_qua = await self._session.execute(
            select(ConversationAnalysisModel).where(ConversationAnalysisModel.id == analysis_id)
        )
        model = ket_qua.scalar_one_or_none()
        return ConversationAnalysisMapper.to_domain(model) if model else None

    async def add(self, analysis: ConversationAnalysis) -> None:
        self._session.add(ConversationAnalysisMapper.to_model(analysis))

    async def list_for_conversation(self, conversation_id: UUID) -> list[ConversationAnalysis]:
        cau = (
            select(ConversationAnalysisModel)
            .where(ConversationAnalysisModel.conversation_id == conversation_id)
            .order_by(ConversationAnalysisModel.created_at.desc())
        )
        ket_qua = await self._session.execute(cau)
        return [ConversationAnalysisMapper.to_domain(m) for m in ket_qua.scalars()]

    def _loc(
        self,
        cau: Select[Any],
        department_ids: list[UUID] | None,
        kem_cho_phan: bool,
        outcomes: Sequence[AnalysisOutcome] | None,
    ) -> Select[Any]:
        if department_ids is not None:
            dieu_kien: ColumnElement[bool] = ConversationAnalysisModel.suggested_department_id.in_(
                department_ids
            )
            if kem_cho_phan:
                # Phòng HIỆN TẠI của hội thoại, không phải phòng đề xuất: nhất quán
                # với quy tắc "phân tích lại" (BaoDamKichHoatPhanTichDuoc).
                cho_phan = select(_HOI_THOAI.c.id).where(_HOI_THOAI.c.department_id.is_(None))
                dieu_kien = or_(dieu_kien, ConversationAnalysisModel.conversation_id.in_(cho_phan))
            cau = cau.where(dieu_kien)
        if outcomes is not None:
            cau = cau.where(ConversationAnalysisModel.outcome.in_([o.value for o in outcomes]))
        return cau

    async def list_for_departments(
        self,
        department_ids: list[UUID] | None,
        limit: int = 50,
        offset: int = 0,
        *,
        kem_cho_phan: bool = False,
        outcomes: Sequence[AnalysisOutcome] | None = None,
    ) -> list[ConversationAnalysis]:
        if department_ids is not None and not department_ids and not kem_cho_phan:
            return []

        cau = self._loc(select(ConversationAnalysisModel), department_ids, kem_cho_phan, outcomes)
        cau = cau.order_by(ConversationAnalysisModel.created_at.desc()).limit(limit).offset(offset)
        ket_qua = await self._session.execute(cau)
        return [ConversationAnalysisMapper.to_domain(m) for m in ket_qua.scalars()]

    async def count_for_departments(
        self,
        department_ids: list[UUID] | None,
        *,
        kem_cho_phan: bool = False,
        outcomes: Sequence[AnalysisOutcome] | None = None,
    ) -> int:
        if department_ids is not None and not department_ids and not kem_cho_phan:
            return 0

        cau = self._loc(
            select(func.count()).select_from(ConversationAnalysisModel),
            department_ids,
            kem_cho_phan,
            outcomes,
        )
        ket_qua = await self._session.execute(cau)
        return int(ket_qua.scalar_one())
