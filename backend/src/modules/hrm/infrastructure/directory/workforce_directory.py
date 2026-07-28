"""Cầu nối hrm → identity: chỗ DUY NHẤT trong hrm được biết identity tồn tại.

Implementation của port ``IWorkforceDirectory``. Nhờ ranh giới này, toàn bộ
domain/application/presentation của hrm không import identity (import-linter
xác nhận); chỉ file infrastructure này đọc dữ liệu identity và dịch sang kiểu
trung lập ``AgentInfo`` của hrm.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.hrm.domain.ports import AgentInfo
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)


class IdentityWorkforceDirectory:
    """Đọc nhân viên/phòng ban từ identity, trả về kiểu trung lập của hrm."""

    def __init__(self, session: AsyncSession) -> None:
        self._user_repo = SqlAlchemyUserRepository(session)
        self._department_repo = SqlAlchemyDepartmentRepository(session)

    async def get_agent(self, user_id: UUID) -> AgentInfo | None:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            return None
        return AgentInfo(
            user_id=user.id,
            department_id=user.department_id,
            role=user.role.value,
            is_active=user.is_active,
        )

    async def department_exists_active(self, department_id: UUID) -> bool:
        department = await self._department_repo.get_by_id(department_id)
        return department is not None and department.is_active

    async def get_manager_of_department(self, department_id: UUID) -> AgentInfo | None:
        """Manager đang hoạt động của một phòng, để định tuyến người duyệt đơn.

        Một phòng có tối đa một Manager active (ràng buộc của #0), nên lấy phần
        tử đầu là đủ.
        """
        managers = await self._user_repo.list_users(
            department_id=department_id, role=Role.MANAGER, is_active=True, limit=1
        )
        if not managers:
            return None
        manager = managers[0]
        return AgentInfo(
            user_id=manager.id,
            department_id=manager.department_id,
            role=manager.role.value,
            is_active=manager.is_active,
        )
