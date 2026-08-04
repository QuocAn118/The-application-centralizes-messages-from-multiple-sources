"""Implementation ``IRollupRepository`` trên PostgreSQL.

Hai ngữ nghĩa ghi KHÁC nhau (chốt ở GĐ2):
- ``bump_*`` = **cộng-delta** (incremental): UPSERT ``ON CONFLICT ... DO UPDATE
  SET col = col + EXCLUDED.col``. Chạy nhiều lần cộng dồn.
- ``ghi_de_*_ngay`` = **ghi đè tuyệt đối** (backfill): xoá sạch dòng của ngày đó
  rồi chèn lại từ nguồn. Chạy lại cho cùng ngày ra cùng kết quả (idempotent).

Khoá gộp có ``department_id`` NULL-able → unique index ``NULLS NOT DISTINCT``;
``on_conflict_do_update(index_elements=...)`` khớp đúng index đó.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.analytics.domain.value_objects.metrics import (
    DailyAgentMetric,
    DailyConversationMetric,
    DateRange,
)
from src.modules.analytics.infrastructure.models.rollup_models import (
    AnalyticsDailyAgentModel,
    AnalyticsDailyConversationModel,
)
from src.shared.domain.identifiers import new_id


class SqlAlchemyRollupRepository:
    """Đọc/ghi hai bảng rollup ngày trên PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ----- Incremental: cộng-delta -----

    async def bump_conversation(self, delta: DailyConversationMetric) -> None:
        stmt = pg_insert(AnalyticsDailyConversationModel).values(
            id=new_id(),
            work_date=delta.work_date,
            department_id=delta.department_id,
            channel_platform=delta.channel_platform,
            inbound_count=delta.inbound_count,
            outbound_count=delta.outbound_count,
            opened_count=delta.opened_count,
            closed_count=delta.closed_count,
        )
        col = AnalyticsDailyConversationModel
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=["work_date", "department_id", "channel_platform"],
                set_={
                    "inbound_count": col.inbound_count + stmt.excluded.inbound_count,
                    "outbound_count": col.outbound_count + stmt.excluded.outbound_count,
                    "opened_count": col.opened_count + stmt.excluded.opened_count,
                    "closed_count": col.closed_count + stmt.excluded.closed_count,
                },
            )
        )

    async def bump_agent(self, delta: DailyAgentMetric) -> None:
        stmt = pg_insert(AnalyticsDailyAgentModel).values(
            id=new_id(),
            work_date=delta.work_date,
            user_id=delta.user_id,
            department_id=delta.department_id,
            handled_count=delta.handled_count,
            assigned_count=delta.assigned_count,
            sum_first_response_seconds=delta.sum_first_response_seconds,
            first_response_samples=delta.first_response_samples,
            sum_resolution_seconds=delta.sum_resolution_seconds,
            resolution_samples=delta.resolution_samples,
        )
        col = AnalyticsDailyAgentModel
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=["work_date", "user_id", "department_id"],
                set_={
                    "handled_count": col.handled_count + stmt.excluded.handled_count,
                    "assigned_count": col.assigned_count + stmt.excluded.assigned_count,
                    "sum_first_response_seconds": col.sum_first_response_seconds
                    + stmt.excluded.sum_first_response_seconds,
                    "first_response_samples": col.first_response_samples
                    + stmt.excluded.first_response_samples,
                    "sum_resolution_seconds": col.sum_resolution_seconds
                    + stmt.excluded.sum_resolution_seconds,
                    "resolution_samples": col.resolution_samples + stmt.excluded.resolution_samples,
                },
            )
        )

    # ----- Backfill: ghi đè tuyệt đối một ngày -----

    async def ghi_de_conversation_ngay(
        self, work_date: date, rows: tuple[DailyConversationMetric, ...]
    ) -> None:
        await self._session.execute(
            delete(AnalyticsDailyConversationModel).where(
                AnalyticsDailyConversationModel.work_date == work_date
            )
        )
        for r in rows:
            self._session.add(
                AnalyticsDailyConversationModel(
                    id=new_id(),
                    work_date=r.work_date,
                    department_id=r.department_id,
                    channel_platform=r.channel_platform,
                    inbound_count=r.inbound_count,
                    outbound_count=r.outbound_count,
                    opened_count=r.opened_count,
                    closed_count=r.closed_count,
                )
            )

    async def ghi_de_agent_ngay(self, work_date: date, rows: tuple[DailyAgentMetric, ...]) -> None:
        await self._session.execute(
            delete(AnalyticsDailyAgentModel).where(AnalyticsDailyAgentModel.work_date == work_date)
        )
        for r in rows:
            self._session.add(
                AnalyticsDailyAgentModel(
                    id=new_id(),
                    work_date=r.work_date,
                    user_id=r.user_id,
                    department_id=r.department_id,
                    handled_count=r.handled_count,
                    assigned_count=r.assigned_count,
                    sum_first_response_seconds=r.sum_first_response_seconds,
                    first_response_samples=r.first_response_samples,
                    sum_resolution_seconds=r.sum_resolution_seconds,
                    resolution_samples=r.resolution_samples,
                )
            )

    # ----- Đọc theo khoảng ngày + lọc phòng -----

    async def doc_conversation(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[DailyConversationMetric, ...]:
        cau = select(AnalyticsDailyConversationModel).where(
            AnalyticsDailyConversationModel.work_date >= khoang.from_date,
            AnalyticsDailyConversationModel.work_date <= khoang.to_date,
        )
        if department_ids is not None:
            cau = cau.where(AnalyticsDailyConversationModel.department_id.in_(department_ids))
        cau = cau.order_by(
            AnalyticsDailyConversationModel.work_date,
            AnalyticsDailyConversationModel.channel_platform,
        )
        ket_qua = await self._session.execute(cau)
        return tuple(
            DailyConversationMetric(
                work_date=m.work_date,
                department_id=m.department_id,
                channel_platform=m.channel_platform,
                inbound_count=m.inbound_count,
                outbound_count=m.outbound_count,
                opened_count=m.opened_count,
                closed_count=m.closed_count,
            )
            for m in ket_qua.scalars()
        )

    async def doc_agent(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[DailyAgentMetric, ...]:
        cau = select(AnalyticsDailyAgentModel).where(
            AnalyticsDailyAgentModel.work_date >= khoang.from_date,
            AnalyticsDailyAgentModel.work_date <= khoang.to_date,
        )
        if department_ids is not None:
            cau = cau.where(AnalyticsDailyAgentModel.department_id.in_(department_ids))
        cau = cau.order_by(AnalyticsDailyAgentModel.work_date, AnalyticsDailyAgentModel.user_id)
        ket_qua = await self._session.execute(cau)
        return tuple(
            DailyAgentMetric(
                work_date=m.work_date,
                user_id=m.user_id,
                department_id=m.department_id,
                handled_count=m.handled_count,
                assigned_count=m.assigned_count,
                sum_first_response_seconds=m.sum_first_response_seconds,
                first_response_samples=m.first_response_samples,
                sum_resolution_seconds=m.sum_resolution_seconds,
                resolution_samples=m.resolution_samples,
            )
            for m in ket_qua.scalars()
        )
