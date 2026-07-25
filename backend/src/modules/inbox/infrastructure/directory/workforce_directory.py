"""Cầu nối inbox → identity: chỗ DUY NHẤT trong inbox được biết identity tồn tại.

Implementation của port ``IWorkforceDirectory``. Nhờ ranh giới này, toàn bộ
domain/application/presentation của inbox không import identity (import-linter
xác nhận); chỉ file infrastructure này đọc dữ liệu identity và dịch sang kiểu
trung lập ``AgentInfo`` của inbox.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.inbox.domain.ports import AgentInfo


class IdentityWorkforceDirectory:
    """Đọc nhân viên/phòng ban từ identity, trả về kiểu trung lập của inbox."""

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
