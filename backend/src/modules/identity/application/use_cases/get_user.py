"""Use case xem chi tiết một người dùng."""

from uuid import UUID

from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError


class GetUser:
    """Xem hồ sơ một người dùng."""

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self, requester: User, user_id: UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Không tìm thấy người dùng.", code="USER_NOT_FOUND")

        if requester.id == user.id:
            return user
        if requester.can_manage(user):
            return user

        raise PermissionDeniedError(
            "Bạn không có quyền xem thông tin người dùng này.",
            code="CANNOT_VIEW_USER",
        )
