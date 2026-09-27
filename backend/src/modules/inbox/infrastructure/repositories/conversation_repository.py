"""Repository hội thoại dùng SQLAlchemy."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.modules.inbox.domain.entities.conversation import (
    Conversation,
    ConversationStatus,
)
from src.modules.inbox.infrastructure.mappers.conversation_mapper import (
    ConversationMapper,
)
from src.modules.inbox.infrastructure.models.conversation_model import ConversationModel
from src.modules.inbox.infrastructure.models.conversation_read_model import (
    ConversationReadModel,
)
from src.modules.inbox.infrastructure.models.customer_model import CustomerModel
from src.modules.inbox.infrastructure.models.message_model import MessageModel


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

    @staticmethod
    def _dieu_kien_tim_kiem(q: str | None) -> list[ColumnElement[bool]]:
        """Lọc theo tên khách hiển thị, bỏ dấu và không phân biệt hoa thường.

        Bỏ dấu cả hai vế vì người dùng Việt thường gõ không dấu — "nguyen" phải
        tìm ra "Nguyễn". Biểu thức khớp đúng index
        ``ix_customers_display_name_unaccent`` (migration ``d4e5f6a7b8c9``);
        đổi biểu thức ở đây mà quên đổi index sẽ khiến truy vấn quét toàn bảng.

        Dùng subquery thay vì JOIN để hình dạng kết quả không đổi (vẫn là các
        hàng ``ConversationModel``), nên sắp xếp và phân trang giữ nguyên.
        ``%``, ``_`` và ``\\`` trong chuỗi tìm được thoát để chúng không trở
        thành ký tự đại diện.
        """
        if q is None:
            return []
        tu_khoa = q.strip()
        if not tu_khoa:
            return []

        an_toan = tu_khoa.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        ten_da_chuan_hoa = func.lower(func.public.immutable_unaccent(CustomerModel.display_name))
        mau = func.lower(func.public.immutable_unaccent(f"%{an_toan}%"))
        khach = (
            select(CustomerModel.id)
            .where(ten_da_chuan_hoa.like(mau, escape="\\"))
            .scalar_subquery()
        )
        return [ConversationModel.customer_id.in_(khach)]

    @staticmethod
    def _dieu_kien_nguoi_phu_trach(
        assigned_to: UUID | None, unassigned: bool
    ) -> list[ColumnElement[bool]]:
        """Lọc "Của tôi" / "Chưa ai nhận" (BE-3). Chồng lên phạm vi, không nới rộng."""
        if unassigned:
            return [ConversationModel.assigned_user_id.is_(None)]
        if assigned_to is not None:
            return [ConversationModel.assigned_user_id == assigned_to]
        return []

    async def list_for_scope(
        self,
        department_ids: list[UUID] | None,
        include_awaiting: bool,
        status: ConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
        q: str | None = None,
        assigned_to: UUID | None = None,
        unassigned: bool = False,
    ) -> list[Conversation]:
        cau = select(ConversationModel).where(
            *self._dieu_kien_pham_vi(department_ids, include_awaiting, status),
            *self._dieu_kien_tim_kiem(q),
            *self._dieu_kien_nguoi_phu_trach(assigned_to, unassigned),
        )
        cau = cau.order_by(ConversationModel.last_message_at.desc()).limit(limit).offset(offset)
        ket_qua = await self._session.execute(cau)
        return [ConversationMapper.to_domain(m) for m in ket_qua.scalars()]

    async def doi_nguoi_phu_trach_neu_chua_doi(
        self,
        conversation_id: UUID,
        nguoi_cu: UUID | None,
        nguoi_moi: UUID | None,
        now: datetime,
    ) -> bool:
        """Đổi người phụ trách CHỈ KHI người hiện tại vẫn là ``nguoi_cu`` (so-và-đổi).

        Hai người đổi cùng lúc (Manager đổi sang B, Admin gỡ): cả hai đọc cùng
        trạng thái, nhưng câu UPDATE có điều kiện chỉ cho MỘT bên thắng; bên còn lại
        nhận ``False`` và báo xung đột — ``assigned_user_id`` không bao giờ lệch với
        timeline. ``IS NOT DISTINCT FROM`` để so được cả NULL.
        """
        cau = (
            update(ConversationModel)
            .where(
                ConversationModel.id == conversation_id,
                ConversationModel.status == ConversationStatus.DANG_MO.value,
                ConversationModel.assigned_user_id.is_not_distinct_from(nguoi_cu),
            )
            .values(assigned_user_id=nguoi_moi, updated_at=now)
            .returning(ConversationModel.id)
        )
        ket_qua = await self._session.execute(cau)
        return ket_qua.scalar_one_or_none() is not None

    async def count_unread_for_scope(
        self, department_ids: list[UUID] | None, include_awaiting: bool, user_id: UUID
    ) -> int:
        """Số hội thoại TRONG PHẠM VI có tin vào chưa đọc với người này (huy hiệu nav).

        Cùng phạm vi với ``GET /inbox`` không lọc; bỏ hội thoại ``DA_DONG`` (đã xử
        lý xong, không làm nhiễu). ``EXISTS`` dừng ở tin chưa đọc đầu tiên.
        """
        # Nối bảng đọc vào CHÍNH hội thoại của tin trong EXISTS. Bản đầu dùng một
        # scalar subquery lồng hai tầng tham chiếu `conversations` — SQLAlchemy không
        # correlate được qua tầng EXISTS và sinh `FROM conversation_reads,
        # conversations` (tích chéo): so với mốc đọc của hội thoại KHÁC. Test tích
        # hợp bắt được (đếm ra 0 thay vì 1).
        doc = aliased(ConversationReadModel)
        co_chua_doc = (
            select(MessageModel.id)
            .outerjoin(
                doc,
                (doc.conversation_id == MessageModel.conversation_id) & (doc.user_id == user_id),
            )
            .where(
                MessageModel.conversation_id == ConversationModel.id,
                MessageModel.direction == "INBOUND",
                (doc.last_read_at.is_(None)) | (MessageModel.created_at > doc.last_read_at),
            )
            .exists()
        )
        cau = (
            select(func.count())
            .select_from(ConversationModel)
            .where(
                *self._dieu_kien_pham_vi(department_ids, include_awaiting, None),
                ConversationModel.status != ConversationStatus.DA_DONG.value,
                co_chua_doc,
            )
        )
        ket_qua = await self._session.execute(cau)
        return int(ket_qua.scalar_one())

    async def count_for_scope(
        self,
        department_ids: list[UUID] | None,
        include_awaiting: bool,
        status: ConversationStatus | None = None,
        q: str | None = None,
        assigned_to: UUID | None = None,
        unassigned: bool = False,
    ) -> int:
        cau = (
            select(func.count())
            .select_from(ConversationModel)
            .where(
                *self._dieu_kien_pham_vi(department_ids, include_awaiting, status),
                *self._dieu_kien_tim_kiem(q),
                *self._dieu_kien_nguoi_phu_trach(assigned_to, unassigned),
            )
        )
        ket_qua = await self._session.execute(cau)
        return int(ket_qua.scalar_one())
