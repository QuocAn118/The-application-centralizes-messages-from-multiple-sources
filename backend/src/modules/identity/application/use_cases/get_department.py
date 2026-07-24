"""Use case xem chi tiết phòng ban."""

from uuid import UUID

from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.department_repository import (
    IDepartmentRepository,
)
from src.shared.application.exceptions import NotFoundError


class GetDepartment:
    """Xem chi tiết một phòng ban."""

    def __init__(self, department_repo: IDepartmentRepository) -> None:
        self._department_repo = department_repo

    async def execute(self, requester: User, department_id: UUID) -> Department:
        phong = await self._department_repo.get_by_id(department_id)
        if phong is None:
            raise NotFoundError("Không tìm thấy phòng ban.", code="DEPARTMENT_NOT_FOUND")
        return phong
