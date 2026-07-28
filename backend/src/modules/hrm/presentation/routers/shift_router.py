"""Endpoint quản lý ca làm việc và phân ca (Manager phòng mình / Admin)."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from src.modules.hrm.application.use_cases.shift_assignment_use_cases import (
    AssignShift,
    CancelShiftAssignment,
    ListShiftAssignments,
)
from src.modules.hrm.application.use_cases.shift_use_cases import (
    CreateShift,
    DeactivateShift,
    ListShifts,
    UpdateShift,
)
from src.modules.hrm.infrastructure.repositories.shift_assignment_repository import (
    SqlAlchemyShiftAssignmentRepository,
)
from src.modules.hrm.infrastructure.repositories.shift_repository import (
    SqlAlchemyShiftRepository,
)
from src.modules.hrm.presentation.dependencies import (
    Actor,
    Clock,
    DbSession,
    Directory,
)
from src.modules.hrm.presentation.schemas.hrm_schemas import (
    AssignShiftRequest,
    CreateShiftRequest,
    ShiftAssignmentResponse,
    ShiftResponse,
    UpdateShiftRequest,
)

router = APIRouter(tags=["shifts"])


@router.get("/shifts", response_model=list[ShiftResponse])
async def liet_ke_ca(
    actor: Actor, session: DbSession, is_active: bool | None = None
) -> list[ShiftResponse]:
    ds = await ListShifts(SqlAlchemyShiftRepository(session)).execute(actor, is_active)
    return [ShiftResponse.from_view(v) for v in ds]


@router.post("/shifts", response_model=ShiftResponse, status_code=201)
async def tao_ca(
    du_lieu: CreateShiftRequest,
    actor: Actor,
    session: DbSession,
    directory: Directory,
    clock: Clock,
) -> ShiftResponse:
    v = await CreateShift(SqlAlchemyShiftRepository(session), directory, clock).execute(
        actor,
        department_id=du_lieu.department_id,
        name=du_lieu.name,
        start_time=du_lieu.start_time,
        end_time=du_lieu.end_time,
    )
    return ShiftResponse.from_view(v)


@router.patch("/shifts/{shift_id}", response_model=ShiftResponse)
async def cap_nhat_ca(
    shift_id: UUID,
    du_lieu: UpdateShiftRequest,
    actor: Actor,
    session: DbSession,
    clock: Clock,
) -> ShiftResponse:
    v = await UpdateShift(SqlAlchemyShiftRepository(session), clock).execute(
        actor,
        shift_id=shift_id,
        name=du_lieu.name,
        start_time=du_lieu.start_time,
        end_time=du_lieu.end_time,
    )
    return ShiftResponse.from_view(v)


@router.post("/shifts/{shift_id}/deactivate", response_model=ShiftResponse)
async def vo_hieu_hoa_ca(
    shift_id: UUID, actor: Actor, session: DbSession, clock: Clock
) -> ShiftResponse:
    v = await DeactivateShift(SqlAlchemyShiftRepository(session), clock).execute(actor, shift_id)
    return ShiftResponse.from_view(v)


@router.post("/shift-assignments", response_model=ShiftAssignmentResponse, status_code=201)
async def phan_ca(
    du_lieu: AssignShiftRequest,
    actor: Actor,
    session: DbSession,
    directory: Directory,
    clock: Clock,
) -> ShiftAssignmentResponse:
    v = await AssignShift(
        SqlAlchemyShiftAssignmentRepository(session),
        SqlAlchemyShiftRepository(session),
        directory,
        clock,
    ).execute(
        actor,
        shift_id=du_lieu.shift_id,
        user_id=du_lieu.user_id,
        work_date=du_lieu.work_date,
    )
    return ShiftAssignmentResponse.from_view(v)


@router.post("/shift-assignments/{assignment_id}/cancel", response_model=ShiftAssignmentResponse)
async def huy_phan_ca(
    assignment_id: UUID, actor: Actor, session: DbSession, clock: Clock
) -> ShiftAssignmentResponse:
    v = await CancelShiftAssignment(SqlAlchemyShiftAssignmentRepository(session), clock).execute(
        actor, assignment_id
    )
    return ShiftAssignmentResponse.from_view(v)


@router.get("/shift-assignments", response_model=list[ShiftAssignmentResponse])
async def liet_ke_phan_ca(
    actor: Actor,
    session: DbSession,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[ShiftAssignmentResponse]:
    ds = await ListShiftAssignments(SqlAlchemyShiftAssignmentRepository(session)).execute(
        actor, date_from=date_from, date_to=date_to
    )
    return [ShiftAssignmentResponse.from_view(v) for v in ds]
