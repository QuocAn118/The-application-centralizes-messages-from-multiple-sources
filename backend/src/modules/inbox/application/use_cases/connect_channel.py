"""Use case: Admin kết nối một kênh mới.

Credential thô (token OA/Page) được mã hoá qua ``ICredentialCipher`` trước khi
tạo entity — entity và DB không bao giờ giữ token thô.
"""

from uuid import UUID

from src.modules.inbox.application.actor import InboxActor
from src.modules.inbox.application.authorization import bao_dam_admin
from src.modules.inbox.domain.entities.channel import Channel
from src.modules.inbox.domain.ports import ICredentialCipher, IWorkforceDirectory
from src.modules.inbox.domain.repositories.channel_repository import IChannelRepository
from src.modules.inbox.domain.value_objects.platform import Platform
from src.shared.application.exceptions import ConflictError, NotFoundError
from src.shared.application.ports import IClock


class ConnectChannel:
    """Kết nối một tài khoản nền tảng (Zalo OA / Facebook Page / Instagram)."""

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
        platform: Platform,
        external_channel_id: str,
        name: str,
        credential: str,
        department_id: UUID | None = None,
    ) -> Channel:
        bao_dam_admin(actor)

        if await self._channel_repo.get_by_external(platform, external_channel_id) is not None:
            raise ConflictError("Kênh này đã được kết nối.", code="CHANNEL_ALREADY_CONNECTED")

        if department_id is not None and not await self._directory.department_exists_active(
            department_id
        ):
            raise NotFoundError(
                "Không tìm thấy phòng ban đang hoạt động.", code="DEPARTMENT_NOT_FOUND"
            )

        channel = Channel.connect(
            platform=platform,
            external_channel_id=external_channel_id,
            name=name,
            department_id=department_id,
            encrypted_credential=self._cipher.encrypt(credential),
            now=self._clock.now(),
        )
        await self._channel_repo.add(channel)
        return channel
