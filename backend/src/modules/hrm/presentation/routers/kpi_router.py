"""Endpoint KPI: đặt mục tiêu (Manager/Admin) và xem tiến độ."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from src.modules.hrm.application.use_cases.kpi_use_cases import (
    GetKpiProgress,
    ListKpiTargets,
    SetKpiTarget,
)
from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.modules.hrm.infrastructure.repositories.kpi_target_repository import (
    SqlAlchemyKpiTargetRepository,
)
from src.modules.hrm.presentation.dependencies import (
    Actor,
    Clock,
    DbSession,
    Directory,
    Performance,
)
from src.modules.hrm.presentation.schemas.hrm_schemas import (
    KpiProgressResponse,
    KpiTargetResponse,
    SetKpiTargetRequest,
)

router = APIRouter(tags=["kpi"])


@router.post("/kpi-targets", response_model=KpiTargetResponse, status_code=201)
async def dat_muc_tieu(
    du_lieu: SetKpiTargetRequest,
    actor: Actor,
    session: DbSession,
    directory: Directory,
    clock: Clock,
) -> KpiTargetResponse:
    v = await SetKpiTarget(SqlAlchemyKpiTargetRepository(session), directory, clock).execute(
        actor,
        subject_type=du_lieu.subject_type,
        subject_id=du_lieu.subject_id,
        metric_type=du_lieu.metric_type,
        period=KpiPeriod(year=du_lieu.period_year, month=du_lieu.period_month),
        target_value=du_lieu.target_value,
    )
    return KpiTargetResponse.from_view(v)


@router.get("/kpi-targets", response_model=list[KpiTargetResponse])
async def liet_ke_muc_tieu(
    actor: Actor,
    session: DbSession,
    period_year: Annotated[int | None, Query()] = None,
    period_month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> list[KpiTargetResponse]:
    period = (
        KpiPeriod(year=period_year, month=period_month)
        if period_year is not None and period_month is not None
        else None
    )
    ds = await ListKpiTargets(SqlAlchemyKpiTargetRepository(session)).execute(actor, period)
    return [KpiTargetResponse.from_view(v) for v in ds]


@router.get("/kpi-progress", response_model=KpiProgressResponse)
async def xem_tien_do(
    actor: Actor,
    session: DbSession,
    directory: Directory,
    performance: Performance,
    subject_type: KpiSubjectType,
    subject_id: UUID,
    metric_type: KpiMetricType,
    period_year: int,
    period_month: Annotated[int, Query(ge=1, le=12)],
) -> KpiProgressResponse:
    v = await GetKpiProgress(
        SqlAlchemyKpiTargetRepository(session), performance, directory
    ).execute(
        actor,
        subject_type=subject_type,
        subject_id=subject_id,
        metric_type=metric_type,
        period=KpiPeriod(year=period_year, month=period_month),
    )
    return KpiProgressResponse.from_view(v)
