"""Endpoint đơn từ: gửi/thu hồi (nhân viên), duyệt/từ chối (một cấp), liệt kê/xem."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from src.modules.hrm.application.use_cases.request_use_cases import (
    ApproveRequest,
    CancelRequest,
    GetRequest,
    ListRequests,
    RejectRequest,
    SubmitRequest,
)
from src.modules.hrm.domain.value_objects.request_kind import RequestStatus
from src.modules.hrm.infrastructure.repositories.request_repository import (
    SqlAlchemyRequestRepository,
)
from src.modules.hrm.presentation.dependencies import (
    Actor,
    Clock,
    DbSession,
    Directory,
    Notifier,
)
from src.modules.hrm.presentation.schemas.hrm_schemas import (
    PageResponse,
    RejectRequestRequest,
    RequestResponse,
    SubmitRequestRequest,
)

router = APIRouter(tags=["requests"])


@router.post("/requests", response_model=RequestResponse, status_code=201)
async def gui_don(
    du_lieu: SubmitRequestRequest,
    actor: Actor,
    session: DbSession,
    directory: Directory,
    notifier: Notifier,
    clock: Clock,
) -> RequestResponse:
    v = await SubmitRequest(
        SqlAlchemyRequestRepository(session), directory, notifier, clock
    ).execute(
        actor,
        request_type=du_lieu.request_type,
        reason=du_lieu.reason,
        leave_start=du_lieu.leave_start,
        leave_end=du_lieu.leave_end,
    )
    return RequestResponse.from_view(v)


@router.get("/requests", response_model=PageResponse[RequestResponse])
async def liet_ke_don(
    actor: Actor,
    session: DbSession,
    status: Annotated[RequestStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[RequestResponse]:
    page = await ListRequests(SqlAlchemyRequestRepository(session)).execute(
        actor, status=status, limit=limit, offset=offset
    )
    return PageResponse(
        items=[RequestResponse.from_view(v) for v in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/requests/{request_id}", response_model=RequestResponse)
async def xem_don(request_id: UUID, actor: Actor, session: DbSession) -> RequestResponse:
    v = await GetRequest(SqlAlchemyRequestRepository(session)).execute(actor, request_id)
    return RequestResponse.from_view(v)


@router.post("/requests/{request_id}/cancel", response_model=RequestResponse)
async def thu_hoi_don(
    request_id: UUID, actor: Actor, session: DbSession, clock: Clock
) -> RequestResponse:
    v = await CancelRequest(SqlAlchemyRequestRepository(session), clock).execute(actor, request_id)
    return RequestResponse.from_view(v)


@router.post("/requests/{request_id}/approve", response_model=RequestResponse)
async def duyet_don(
    request_id: UUID,
    actor: Actor,
    session: DbSession,
    directory: Directory,
    notifier: Notifier,
    clock: Clock,
) -> RequestResponse:
    v = await ApproveRequest(
        SqlAlchemyRequestRepository(session), directory, notifier, clock
    ).execute(actor, request_id)
    return RequestResponse.from_view(v)


@router.post("/requests/{request_id}/reject", response_model=RequestResponse)
async def tu_choi_don(
    request_id: UUID,
    du_lieu: RejectRequestRequest,
    actor: Actor,
    session: DbSession,
    directory: Directory,
    notifier: Notifier,
    clock: Clock,
) -> RequestResponse:
    v = await RejectRequest(
        SqlAlchemyRequestRepository(session), directory, notifier, clock
    ).execute(actor, request_id, reason=du_lieu.reason)
    return RequestResponse.from_view(v)
