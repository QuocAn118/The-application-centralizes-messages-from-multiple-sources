"""Endpoint báo cáo analytics (JSON đọc-chỉ) dưới ``/api/v1/analytics/*``.

Chỉ Manager (phòng mình) / Admin (mọi phòng); Staff bị 403. Use case tự ép phạm
vi phòng (``pham_vi_phong_bao_cao``). ``POST /rollups/rebuild`` là công cụ vận
hành chỉ cho Admin, chặn khoảng ngày quá dài.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Request

from src.modules.analytics.application.actor import ActorRole
from src.modules.analytics.domain.value_objects.metrics import DateRange
from src.modules.analytics.presentation.dependencies import (
    Actor,
    DateRangeParam,
    DbSession,
    get_agent_report,
    get_conversation_report,
    get_rebuild,
    get_request_report,
    get_workforce_report,
)
from src.modules.analytics.presentation.schemas.analytics_schemas import (
    AgentReportItem,
    ConversationReportItem,
    RebuildResponse,
    RequestReportItem,
    WorkforceReportItem,
)
from src.shared.application.exceptions import ApplicationError, PermissionDeniedError

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Chặn rebuild khoảng ngày quá dài (mỗi ngày 2+ truy vấn quét nguồn — tránh một
# lệnh vận hành quét cả nhiều năm). ~15 tháng đủ cho backfill một kỳ.
_REBUILD_MAX_NGAY = 460


@router.get("/conversations", response_model=list[ConversationReportItem])
async def bao_cao_hoi_thoai(
    actor: Actor,
    session: DbSession,
    khoang: DateRangeParam,
    request: Request,
    department_id: UUID | None = None,
) -> list[ConversationReportItem]:
    use_case = get_conversation_report(request, session)
    rows = await use_case.execute(actor, khoang, department_id)
    return [ConversationReportItem.from_row(r) for r in rows]


@router.get("/agents", response_model=list[AgentReportItem])
async def bao_cao_nhan_vien(
    actor: Actor,
    session: DbSession,
    khoang: DateRangeParam,
    request: Request,
    department_id: UUID | None = None,
) -> list[AgentReportItem]:
    use_case = get_agent_report(request, session)
    rows = await use_case.execute(actor, khoang, department_id)
    return [AgentReportItem.from_performance(p) for p in rows]


@router.get("/workforce", response_model=list[WorkforceReportItem])
async def bao_cao_ca_kpi(
    actor: Actor,
    session: DbSession,
    khoang: DateRangeParam,
    request: Request,
    department_id: UUID | None = None,
) -> list[WorkforceReportItem]:
    use_case = get_workforce_report(request, session)
    rows = await use_case.execute(actor, khoang, department_id)
    return [WorkforceReportItem.from_row(r) for r in rows]


@router.get("/requests", response_model=list[RequestReportItem])
async def bao_cao_don_tu(
    actor: Actor,
    session: DbSession,
    khoang: DateRangeParam,
    request: Request,
    department_id: UUID | None = None,
) -> list[RequestReportItem]:
    use_case = get_request_report(request, session)
    rows = await use_case.execute(actor, khoang, department_id)
    return [RequestReportItem.from_row(r) for r in rows]


@router.post("/rollups/rebuild", response_model=RebuildResponse)
async def chay_backfill(
    actor: Actor,
    session: DbSession,
    request: Request,
    from_date: date,
    to_date: date,
) -> RebuildResponse:
    """Dựng lại rollup một khoảng ngày (vận hành) — CHỈ Admin, chặn range quá dài."""
    if actor.role is not ActorRole.ADMIN:
        raise PermissionDeniedError(
            "Chỉ quản trị viên được chạy dựng lại rollup.",
            code="ANALYTICS_REBUILD_ADMIN_ONLY",
        )
    khoang = DateRange(from_date=from_date, to_date=to_date)
    if (khoang.to_date - khoang.from_date).days + 1 > _REBUILD_MAX_NGAY:
        raise ApplicationError(
            f"Khoảng ngày quá dài (tối đa {_REBUILD_MAX_NGAY} ngày một lần).",
            code="ANALYTICS_REBUILD_RANGE_TOO_LONG",
        )
    use_case = get_rebuild(request, session)
    so_ngay = await use_case.execute(khoang)
    return RebuildResponse(days_rebuilt=so_ngay)
