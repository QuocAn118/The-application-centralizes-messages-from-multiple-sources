"""Use case cập nhật thông tin hồ sơ."""

from uuid import UUID

from src.modules.identity.domain.entities.audit_log import AuditAction, AuditLog
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.repositories.audit_log_repository import (
    IAuditLogRepository,
)
from src.modules.identity.domain.repositories.user_repository import IUserRepository
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.application.ports import IClock


class UpdateUser:
    """Sửa họ tên và số điện thoại.

    Không đụng tới email, vai trò hay phòng ban — mỗi thứ đó có use case riêng
    vì chúng mang quy tắc nghiệp vụ khác nhau.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        audit_repo: IAuditLogRepository,
        clock: IClock,
    ) -> None:
        self._user_repo = user_repo
        self._audit_repo = audit_repo
        self._clock = clock

    async def execute(
        self,
        requester: User,
        user_id: UUID,
        full_name: str | None = None,
        phone: str | None = None,
    ) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(
                "Không tìm thấy người dùng.", code="USER_NOT_FOUND"
            )

        la_chinh_minh = requester.id == user.id
        if not la_chinh_minh and not requester.can_manage(user):
            raise PermissionDeniedError(
                "Bạn không có quyền sửa thông tin người dùng này.",
                code="CANNOT_MANAGE_USER",
            )

        bay_gio = self._clock.now()
        truoc = {"full_name": user.full_name, "phone": user.phone}
        user.update_profile(full_name=full_name, phone=phone, now=bay_gio)
        await self._user_repo.update(user)

        await self._audit_repo.add(
            AuditLog.record(
                action=AuditAction.USER_UPDATED,
                actor_id=requester.id,
                resource_type="user",
                resource_id=str(user.id),
                now=bay_gio,
                changes={
                    "truoc": truoc,
                    "sau": {"full_name": user.full_name, "phone": user.phone},
                },
            )
        )
        return user
