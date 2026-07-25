"""Repository tin nhắn và tệp đính kèm dùng SQLAlchemy."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.attachment import Attachment
from src.modules.inbox.domain.entities.message import Message
from src.modules.inbox.infrastructure.mappers.message_mapper import (
    AttachmentMapper,
    MessageMapper,
)
from src.modules.inbox.infrastructure.models.attachment_model import AttachmentModel
from src.modules.inbox.infrastructure.models.message_model import MessageModel


class SqlAlchemyMessageRepository:
    """Truy xuất tin nhắn và tệp đính kèm từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: Message, attachments: list[Attachment]) -> None:
        """Lưu một tin cùng các tệp đính kèm của nó trong một thao tác.

        Không dùng ORM relationship nên phải flush tin trước để hàng ``messages``
        tồn tại khi chèn ``attachments`` (khoá ngoại). Flush không phải commit —
        giao dịch vẫn do router chốt.
        """
        self._session.add(MessageMapper.to_model(message))
        if attachments:
            await self._session.flush()
            for attachment in attachments:
                self._session.add(AttachmentMapper.to_model(attachment))

    async def exists_external(self, external_message_id: str) -> bool:
        ket_qua = await self._session.execute(
            select(func.count())
            .select_from(MessageModel)
            .where(MessageModel.external_message_id == external_message_id)
        )
        return ket_qua.scalar_one() > 0

    async def list_for_conversation(
        self, conversation_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Message]:
        cau = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at)
            .limit(limit)
            .offset(offset)
        )
        ket_qua = await self._session.execute(cau)
        return [MessageMapper.to_domain(m) for m in ket_qua.scalars()]

    async def list_attachments(self, message_id: UUID) -> list[Attachment]:
        cau = (
            select(AttachmentModel)
            .where(AttachmentModel.message_id == message_id)
            .order_by(AttachmentModel.created_at)
        )
        ket_qua = await self._session.execute(cau)
        return [AttachmentMapper.to_domain(m) for m in ket_qua.scalars()]
