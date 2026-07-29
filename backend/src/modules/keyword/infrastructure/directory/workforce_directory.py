"""Cầu nối keyword → identity: chỗ DUY NHẤT trong keyword được biết identity tồn tại.

Implementation của port ``IWorkforceDirectory``. Nhờ ranh giới này, toàn bộ
domain/application/presentation của keyword không import identity (import-linter
xác nhận); chỉ file infrastructure này đọc dữ liệu identity. Dùng để *gác* kết
quả LLM (phòng LLM chọn phải tồn tại + đang hoạt động) và để dựng danh tính người
gọi (``get_agent``) khi tầng HTTP phân quyền.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.modules.keyword.domain.ports import AgentInfo


class IdentityWorkforceDirectory:
    """Đọc phòng ban/nhân viên từ identity, trả kiểu trung lập của keyword."""

    def __init__(self, session: AsyncSession) -> None:
        self._department_repo = SqlAlchemyDepartmentRepository(session)
        self._user_repo = SqlAlchemyUserRepository(session)

    async def department_exists_active(self, department_id: UUID) -> bool:
        department = await self._department_repo.get_by_id(department_id)
        return department is not None and department.is_active

    async def get_agent(self, user_id: UUID) -> AgentInfo | None:
        """Danh tính tối thiểu của một nhân viên, cho tầng HTTP dựng ``KeywordActor``."""
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            return None
        return AgentInfo(
            user_id=user.id,
            department_id=user.department_id,
            role=user.role.value,
            is_active=user.is_active,
        )
