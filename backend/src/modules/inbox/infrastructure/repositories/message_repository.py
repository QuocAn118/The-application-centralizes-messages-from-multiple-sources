"""Repository tin nhắn và tệp đính kèm dùng SQLAlchemy."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

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
        self, conversation_id: UUID, limit: int = 50, offset: int = 0, newest: bool = False
    ) -> list[Message]:
        """Tin của một hội thoại, luôn trả theo thứ tự cũ → mới.

        ``newest=True`` lấy ``limit`` tin MỚI NHẤT (rồi vẫn xếp cũ → mới để
        hiển thị). Cần cho khung chat: hội thoại dài hơn ``limit`` mà lấy từ
        đầu thì người dùng chỉ thấy tin cũ nhất và không bao giờ tới được tin
        mới — đúng thứ họ cần đọc.
        """
        if newest:
            con = (
                select(MessageModel)
                .where(MessageModel.conversation_id == conversation_id)
                # ``id`` phá hoà khi nhiều tin chung một mốc (chèn cùng lô).
                .order_by(MessageModel.created_at.desc(), MessageModel.id.desc())
                .limit(limit)
                .offset(offset)
                .subquery()
            )
            model = aliased(MessageModel, con)
            cau = select(model).order_by(model.created_at, model.id)
        else:
            cau = (
                select(MessageModel)
                .where(MessageModel.conversation_id == conversation_id)
                .order_by(MessageModel.created_at, MessageModel.id)
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

    async def last_texts_for_conversations(self, conversation_ids: list[UUID]) -> dict[UUID, str]:
        """Trả nội dung chữ của tin CUỐI mỗi hội thoại, cho cả danh sách.

        Một truy vấn cho cả trang thay vì mỗi dòng một lần: danh sách 25 dòng
        mà hỏi từng dòng là 25 vòng tới cơ sở dữ liệu chỉ để hiện dòng preview.

        ``DISTINCT ON`` là cách của PostgreSQL để lấy hàng đầu tiên trong mỗi
        nhóm — ở đây là tin mới nhất của mỗi hội thoại. Tin chỉ có ảnh (``text``
        rỗng/NULL) bị loại, nên preview lấy tin có chữ gần nhất.
        """
        if not conversation_ids:
            return {}

        cau = (
            select(MessageModel.conversation_id, MessageModel.text)
            .where(
                MessageModel.conversation_id.in_(conversation_ids),
                MessageModel.text.isnot(None),
                MessageModel.text != "",
            )
            .distinct(MessageModel.conversation_id)
            # ``id`` làm chốt phá hoà: tin chèn cùng lô chia nhau một
            # ``created_at`` (server_default now() cố định trong một giao dịch),
            # nên thiếu chốt này preview sẽ nhảy qua lại giữa các lần tải.
            .order_by(
                MessageModel.conversation_id,
                MessageModel.created_at.desc(),
                MessageModel.id.desc(),
            )
        )
        ket_qua = await self._session.execute(cau)
        return {hang.conversation_id: hang.text for hang in ket_qua}

    async def get_attachment_with_conversation(
        self, attachment_id: UUID
    ) -> tuple[Attachment, UUID] | None:
        """Trả ``(tệp, conversation_id)`` — ``None`` nếu không có.

        Trả kèm mã hội thoại trong CÙNG một truy vấn để nơi gọi kiểm được quyền
        mà không phải tự nối bảng: người xin tệp phải có quyền trên đúng hội
        thoại chứa nó.
        """
        cau = (
            select(AttachmentModel, MessageModel.conversation_id)
            .join(MessageModel, AttachmentModel.message_id == MessageModel.id)
            .where(AttachmentModel.id == attachment_id)
        )
        ket_qua = await self._session.execute(cau)
        hang = ket_qua.first()
        if hang is None:
            return None
        model, conversation_id = hang
        return AttachmentMapper.to_domain(model), conversation_id
