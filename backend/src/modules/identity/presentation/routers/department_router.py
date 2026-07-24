"""Endpoint quản lý phòng ban và tra cứu nhật ký."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from src.modules.identity.application.use_cases.create_department import (
    CreateDepartment,
)
from src.modules.identity.application.use_cases.deactivate_department import (
    DeactivateDepartment,
)
from src.modules.identity.application.use_cases.get_department import GetDepartment
from src.modules.identity.application.use_cases.list_audit_logs import ListAuditLogs
from src.modules.identity.application.use_cases.list_departments import ListDepartments
from src.modules.identity.application.use_cases.update_department import (
    UpdateDepartment,
)
from src.modules.identity.domain.entities.audit_log import AuditAction
from src.modules.identity.infrastructure.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.identity.presentation.dependencies import CurrentUser, DbSession
from src.modules.identity.presentation.schemas.common import PageResponse
from src.modules.identity.presentation.schemas.department_schemas import (
    CreateDepartmentRequest,
    DepartmentResponse,
    UpdateDepartmentRequest,
)
from src.shared.infrastructure.clock import SystemClock

router = APIRouter(tags=["departments"])


@router.get("/departments", response_model=PageResponse[DepartmentResponse])
async def danh_sach_phong_ban(
    nguoi_goi: CurrentUser,
    session: DbSession,
    is_active: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[DepartmentResponse]:
    trang = await ListDepartments(SqlAlchemyDepartmentRepository(session)).execute(
        requester=nguoi_goi, is_active=is_active, limit=limit, offset=offset
    )
    return PageResponse(
        items=[DepartmentResponse.from_entity(d) for d in trang.items],
        total=trang.total,
        limit=trang.limit,
        offset=trang.offset,
    )


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def tao_phong_ban(
    du_lieu: CreateDepartmentRequest, nguoi_goi: CurrentUser, session: DbSession
) -> DepartmentResponse:
    use_case = CreateDepartment(
        department_repo=SqlAlchemyDepartmentRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    phong = await use_case.execute(
        requester=nguoi_goi, name=du_lieu.name, description=du_lieu.description
    )
    return DepartmentResponse.from_entity(phong)


@router.get("/departments/{department_id}", response_model=DepartmentResponse)
async def xem_phong_ban(
    department_id: UUID, nguoi_goi: CurrentUser, session: DbSession
) -> DepartmentResponse:
    phong = await GetDepartment(SqlAlchemyDepartmentRepository(session)).execute(
        requester=nguoi_goi, department_id=department_id
    )
    return DepartmentResponse.from_entity(phong)


@router.patch("/departments/{department_id}", response_model=DepartmentResponse)
async def sua_phong_ban(
    department_id: UUID,
    du_lieu: UpdateDepartmentRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
) -> DepartmentResponse:
    use_case = UpdateDepartment(
        department_repo=SqlAlchemyDepartmentRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    phong = await use_case.execute(
        requester=nguoi_goi,
        department_id=department_id,
        name=du_lieu.name,
        description=du_lieu.description,
    )
    return DepartmentResponse.from_entity(phong)


@router.post("/departments/{department_id}/deactivate", response_model=DepartmentResponse)
async def vo_hieu_hoa_phong_ban(
    department_id: UUID, nguoi_goi: CurrentUser, session: DbSession
) -> DepartmentResponse:
    use_case = DeactivateDepartment(
        department_repo=SqlAlchemyDepartmentRepository(session),
        user_repo=SqlAlchemyUserRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    phong = await use_case.execute(requester=nguoi_goi, department_id=department_id)
    return DepartmentResponse.from_entity(phong)


@router.get("/audit-logs", tags=["audit"])
async def danh_sach_nhat_ky(
    nguoi_goi: CurrentUser,
    session: DbSession,
    actor_id: UUID | None = None,
    action: AuditAction | None = None,
    resource_type: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    """Tra cứu nhật ký hệ thống. Chỉ quản trị viên."""
    trang = await ListAuditLogs(SqlAlchemyAuditLogRepository(session)).execute(
        requester=nguoi_goi,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "id": str(e.id),
                "action": e.action.value,
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "changes": e.changes,
                "ip_address": e.ip_address,
                "created_at": e.created_at.isoformat(),
            }
            for e in trang.items
        ],
        "total": trang.total,
        "limit": trang.limit,
        "offset": trang.offset,
    }
