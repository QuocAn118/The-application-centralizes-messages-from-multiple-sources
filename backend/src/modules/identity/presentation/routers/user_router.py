"""Endpoint quản lý người dùng."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from src.modules.identity.application.use_cases.assign_user_to_department import (
    AssignUserToDepartment,
)
from src.modules.identity.application.use_cases.change_user_role import ChangeUserRole
from src.modules.identity.application.use_cases.create_user import CreateUser
from src.modules.identity.application.use_cases.deactivate_user import DeactivateUser
from src.modules.identity.application.use_cases.get_user import GetUser
from src.modules.identity.application.use_cases.list_users import ListUsers
from src.modules.identity.application.use_cases.reactivate_user import ReactivateUser
from src.modules.identity.application.use_cases.reset_user_password import (
    ResetUserPassword,
)
from src.modules.identity.application.use_cases.update_user import UpdateUser
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.identity.infrastructure.security.password_hasher import (
    BcryptPasswordHasher,
)
from src.modules.identity.presentation.dependencies import (
    CurrentUser,
    DbSession,
    get_password_hasher,
)
from src.modules.identity.presentation.schemas.auth_schemas import UserResponse
from src.modules.identity.presentation.schemas.common import PageResponse
from src.modules.identity.presentation.schemas.user_schemas import (
    AssignDepartmentRequest,
    ChangeRoleRequest,
    CreateUserRequest,
    ResetPasswordRequest,
    UpdateUserRequest,
)
from src.shared.infrastructure.clock import SystemClock

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=PageResponse[UserResponse])
async def danh_sach_nguoi_dung(
    nguoi_goi: CurrentUser,
    session: DbSession,
    department_id: UUID | None = None,
    role: Role | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[UserResponse]:
    """Liệt kê người dùng trong phạm vi quyền của người gọi."""
    trang = await ListUsers(SqlAlchemyUserRepository(session)).execute(
        requester=nguoi_goi,
        department_id=department_id,
        role=role,
        is_active=is_active,
        search=search,
        limit=limit,
        offset=offset,
    )
    return PageResponse(
        items=[UserResponse.from_entity(u) for u in trang.items],
        total=trang.total,
        limit=trang.limit,
        offset=trang.offset,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def tao_nguoi_dung(
    du_lieu: CreateUserRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
    hasher: Annotated[BcryptPasswordHasher, Depends(get_password_hasher)],
) -> UserResponse:
    """Tạo tài khoản mới. Chỉ quản trị viên."""
    use_case = CreateUser(
        user_repo=SqlAlchemyUserRepository(session),
        department_repo=SqlAlchemyDepartmentRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        hasher=hasher,
        clock=SystemClock(),
    )
    user = await use_case.execute(
        requester=nguoi_goi,
        email=du_lieu.email,
        full_name=du_lieu.full_name,
        role=du_lieu.role,
        department_id=du_lieu.department_id,
        password=du_lieu.password,
        phone=du_lieu.phone,
    )
    return UserResponse.from_entity(user)


@router.get("/{user_id}", response_model=UserResponse)
async def xem_nguoi_dung(
    user_id: UUID, nguoi_goi: CurrentUser, session: DbSession
) -> UserResponse:
    user = await GetUser(SqlAlchemyUserRepository(session)).execute(
        requester=nguoi_goi, user_id=user_id
    )
    return UserResponse.from_entity(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def sua_nguoi_dung(
    user_id: UUID,
    du_lieu: UpdateUserRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
) -> UserResponse:
    use_case = UpdateUser(
        user_repo=SqlAlchemyUserRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    user = await use_case.execute(
        requester=nguoi_goi,
        user_id=user_id,
        full_name=du_lieu.full_name,
        phone=du_lieu.phone,
    )
    return UserResponse.from_entity(user)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def vo_hieu_hoa(
    user_id: UUID, nguoi_goi: CurrentUser, session: DbSession
) -> UserResponse:
    use_case = DeactivateUser(
        user_repo=SqlAlchemyUserRepository(session),
        refresh_token_repo=SqlAlchemyRefreshTokenRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    return UserResponse.from_entity(
        await use_case.execute(requester=nguoi_goi, user_id=user_id)
    )


@router.post("/{user_id}/reactivate", response_model=UserResponse)
async def kich_hoat_lai(
    user_id: UUID, nguoi_goi: CurrentUser, session: DbSession
) -> UserResponse:
    use_case = ReactivateUser(
        user_repo=SqlAlchemyUserRepository(session),
        department_repo=SqlAlchemyDepartmentRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    return UserResponse.from_entity(
        await use_case.execute(requester=nguoi_goi, user_id=user_id)
    )


@router.patch("/{user_id}/role", response_model=UserResponse)
async def doi_vai_tro(
    user_id: UUID,
    du_lieu: ChangeRoleRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
) -> UserResponse:
    use_case = ChangeUserRole(
        user_repo=SqlAlchemyUserRepository(session),
        department_repo=SqlAlchemyDepartmentRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    return UserResponse.from_entity(
        await use_case.execute(
            requester=nguoi_goi,
            user_id=user_id,
            new_role=du_lieu.role,
            department_id=du_lieu.department_id,
        )
    )


@router.patch("/{user_id}/department", response_model=UserResponse)
async def chuyen_phong_ban(
    user_id: UUID,
    du_lieu: AssignDepartmentRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
) -> UserResponse:
    use_case = AssignUserToDepartment(
        user_repo=SqlAlchemyUserRepository(session),
        department_repo=SqlAlchemyDepartmentRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        clock=SystemClock(),
    )
    return UserResponse.from_entity(
        await use_case.execute(
            requester=nguoi_goi, user_id=user_id, department_id=du_lieu.department_id
        )
    )


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def dat_lai_mat_khau(
    user_id: UUID,
    du_lieu: ResetPasswordRequest,
    nguoi_goi: CurrentUser,
    session: DbSession,
    hasher: Annotated[BcryptPasswordHasher, Depends(get_password_hasher)],
) -> Response:
    use_case = ResetUserPassword(
        user_repo=SqlAlchemyUserRepository(session),
        refresh_token_repo=SqlAlchemyRefreshTokenRepository(session),
        audit_repo=SqlAlchemyAuditLogRepository(session),
        hasher=hasher,
        clock=SystemClock(),
    )
    await use_case.execute(
        requester=nguoi_goi, user_id=user_id, new_password=du_lieu.new_password
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
