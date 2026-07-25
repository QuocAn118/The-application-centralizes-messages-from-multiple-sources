"""Use case: Admin cập nhật một kênh (tên, phòng, credential).

Mỗi trường ``None`` nghĩa là giữ nguyên. Credential mới được mã hoá lại trước
khi lưu; token thô không rời khỏi use case.
"""

from uuid import UUID

from src.modules.inbox.application.actor import InboxActor
from src.modules.inbox.application.authorization import bao_dam_admin
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.ports import ICredentialCipher, IWorkforceDirectory
from src.modules.inbox.domain.repositories.channel_repository import IChannelRepository
from src.shared.application.exceptions import NotFoundError
from src.shared.application.ports import IClock


class UpdateChannel:
    """Đổi tên, đổi phòng phụ trách, hoặc thay credential của một kênh."""

    def __init__(
        self,
        channel_repo: IChannelRepository,
        directory: IWorkforceDirectory,
        cipher: ICredentialCipher,
        clock: IClock,
    ) -> None:
        self._channel_repo = channel_repo
        self._directory = directory
        self._cipher = cipher
        self._clock = clock

    async def execute(
        self,
        actor: InboxActor,
        channel_id: UUID,
        name: str | None = None,
        credential: str | None = None,
        department_id: UUID | None = None,
        clear_department: bool = False,
    ) -> Channel:
        bao_dam_admin(actor)

        channel = await self._channel_repo.get_by_id(channel_id)
        if channel is None:
            raise NotFoundError("Không tìm thấy kênh.", code="CHANNEL_NOT_FOUND")

        now = self._clock.now()

        if name is not None:
            channel.rename(name, now)
        if credential is not None:
            channel.update_credential(self._cipher.encrypt(credential), now)
        if clear_department:
            channel.assign_department(None, now)
        elif department_id is not None:
            if not await self._directory.department_exists_active(department_id):
                raise NotFoundError(
                    "Không tìm thấy phòng ban đang hoạt động.", code="DEPARTMENT_NOT_FOUND"
                )
            channel.assign_department(department_id, now)

        await self._channel_repo.update(channel)
        return channel
