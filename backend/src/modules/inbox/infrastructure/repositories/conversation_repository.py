"""Repository hội thoại dùng SQLAlchemy."""

from uuid import UUID

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inbox.domain.entities.conversation import (
    Conversation,
    ConversationStatus,
)
from src.modules.inbox.infrastructure.mappers.conversation_mapper import (
    ConversationMapper,
)
from src.modules.inbox.infrastructure.models.conversation_model import ConversationModel


class SqlAlchemyConversationRepository:
    """Truy xuất hội thoại từ PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lay_model(self, conversation_id: UUID) -> ConversationModel | None:
        ket_qua = await self._session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        return ket_qua.scalar_one_or_none()

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        model = await self._lay_model(conversation_id)
        return ConversationMapper.to_domain(model) if model else None

    async def get_open_for(self, channel_id: UUID, customer_id: UUID) -> Conversation | None:
        ket_qua = await self._session.execute(
            select(ConversationModel).where(
                ConversationModel.channel_id == channel_id,
                ConversationModel.customer_id == customer_id,
                ConversationModel.status != ConversationStatus.DA_DONG.value,
            )
        )
        model = ket_qua.scalars().first()
        return ConversationMapper.to_domain(model) if model else None

    async def add(self, conversation: Conversation) -> None:
        self._session.add(ConversationMapper.to_model(conversation))

    async def update(self, conversation: Conversation) -> None:
        model = await self._lay_model(conversation.id)
        if model is None:
            raise ValueError(f"Không tìm thấy hội thoại {conversation.id} để cập nhật.")
        ConversationMapper.update_model(model, conversation)

    @staticmethod
    def _dieu_kien_pham_vi(
        department_ids: list[UUID] | None,
        include_awaiting: bool,
        status: ConversationStatus | None,
    ) -> list[ColumnElement[bool]]:
        """Dựng điều kiện WHERE khớp đúng luật phạm vi ở use case ListInbox.

        ``department_ids=None`` là Admin — không giới hạn phòng. Danh sách rỗng
        nghĩa là không phòng nào; khi ấy chỉ còn mục chờ-phân (nếu được gộp).
        """
        dieu_kien: list[ColumnElement[bool]] = []

        if department_ids is not None:
            thuoc_phong = (
                ConversationModel.department_id.in_(department_ids)
                if department_ids
                else func.false()
            )
            la_cho_phan = ConversationModel.status == ConversationStatus.CHO_PHAN.value
            if include_awaiting:
                dieu_kien.append(or_(thuoc_phong, la_cho_phan))
            else:
                dieu_kien.append(thuoc_phong)

        if status is not None:
            dieu_kien.append(ConversationModel.status == status.value)

        return dieu_kien

    async def list_for_scope(
        self,
        department_ids: list[UUID] | None,
        include_awaiting: bool,
        status: ConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        cau = select(ConversationModel).where(
            *self._dieu_kien_pham_vi(department_ids, include_awaiting, status)
        )
        cau = cau.order_by(ConversationModel.last_message_at.desc()).limit(limit).offset(offset)
        ket_qua = await self._session.execute(cau)
        return [ConversationMapper.to_domain(m) for m in ket_qua.scalars()]

    async def count_for_scope(
        self,
        department_ids: list[UUID] | None,
        include_awaiting: bool,
        status: ConversationStatus | None = None,
    ) -> int:
        cau = (
            select(func.count())
            .select_from(ConversationModel)
            .where(*self._dieu_kien_pham_vi(department_ids, include_awaiting, status))
        )
        ket_qua = await self._session.execute(cau)
        return int(ket_qua.scalar_one())
