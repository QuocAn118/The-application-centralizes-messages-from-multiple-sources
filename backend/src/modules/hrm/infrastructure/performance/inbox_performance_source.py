"""Cầu nối hrm → inbox: chỗ DUY NHẤT trong hrm được biết inbox tồn tại.

Implementation của port ``IPerformanceSource``. Nhờ ranh giới này, toàn bộ
domain/application/presentation của hrm không import inbox (import-linter xác
nhận); chỉ file infrastructure này truy vấn dữ liệu inbox để tính KPI thực đạt.

Đổi nguồn hiệu suất (thêm #2/#5) sau chỉ đụng file này, không đụng use case KPI.

Hai chỉ số: ``CONVERSATIONS_CLOSED`` (đếm hội thoại đóng theo ``closed_at`` chính
xác) và ``AVG_RESPONSE_MINUTES`` (phút phản hồi trung bình: tin INBOUND đầu → tin
OUTBOUND đầu, quy cho người phản hồi, event-time theo ngày tin OUTBOUND đầu).
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.hrm.domain.value_objects.kpi import KpiMetricType, KpiPeriod
from src.modules.inbox.infrastructure.models.conversation_model import ConversationModel
from src.modules.inbox.infrastructure.models.message_model import MessageModel

# Trạng thái "đã xử lý xong" của hội thoại inbox — hằng chuỗi để không import
# enum của inbox (chỉ cần giá trị, không cần kiểu).
_DA_DONG = "DA_DONG"
# Chiều tin — hằng chuỗi (không import enum inbox).
_INBOUND = "INBOUND"
_OUTBOUND = "OUTBOUND"


def _khoang_ky(period: KpiPeriod) -> tuple[datetime, datetime]:
    """Nửa khoảng ``[đầu tháng, đầu tháng sau)`` theo UTC cho một kỳ.

    Dùng nửa khoảng với biên phải mở (``<``) thay vì biên cuối tháng cứng: không
    phụ thuộc độ chính xác của cột thời gian và không đếm nhầm mốc ``00:00:00``
    đầu tháng sau.
    """
    dau = datetime(period.year, period.month, 1, tzinfo=UTC)
    if period.month == 12:
        het = datetime(period.year + 1, 1, 1, tzinfo=UTC)
    else:
        het = datetime(period.year, period.month + 1, 1, tzinfo=UTC)
    return dau, het


class InboxPerformanceSource:
    """Tính KPI thực đạt từ dữ liệu hội thoại của inbox."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_metric_for_user(
        self, user_id: UUID, metric_type: KpiMetricType, period: KpiPeriod
    ) -> Decimal | None:
        if metric_type is KpiMetricType.CONVERSATIONS_CLOSED:
            return await self._dem_hoi_thoai_dong(period, user_id=user_id)
        return await self._phut_phan_hoi_tb(period, user_id=user_id)

    async def get_metric_for_department(
        self, department_id: UUID, metric_type: KpiMetricType, period: KpiPeriod
    ) -> Decimal | None:
        if metric_type is KpiMetricType.CONVERSATIONS_CLOSED:
            return await self._dem_hoi_thoai_dong(period, department_id=department_id)
        return await self._phut_phan_hoi_tb(period, department_id=department_id)

    async def _dem_hoi_thoai_dong(
        self,
        period: KpiPeriod,
        user_id: UUID | None = None,
        department_id: UUID | None = None,
    ) -> Decimal:
        """Số hội thoại đóng trong kỳ, gán cho một nhân viên hoặc thuộc một phòng.

        Mốc đóng = ``closed_at`` (chính xác, đặt khi ``close()``; xoá khi mở lại).
        Dòng cũ trước khi có cột ``closed_at`` đã backfill = ``updated_at``, nên
        ``COALESCE(closed_at, updated_at)`` cho các dòng cũ vẫn dùng proxy. Lọc
        ``status = DA_DONG`` để chỉ đếm hội thoại HIỆN đang đóng (mở lại đã xoá
        ``closed_at`` và đổi trạng thái).
        """
        dau, het = _khoang_ky(period)
        moc_dong = func.coalesce(ConversationModel.closed_at, ConversationModel.updated_at)
        cau = (
            select(func.count())
            .select_from(ConversationModel)
            .where(
                ConversationModel.status == _DA_DONG,
                moc_dong >= dau,
                moc_dong < het,
            )
        )
        if user_id is not None:
            cau = cau.where(ConversationModel.assigned_user_id == user_id)
        if department_id is not None:
            cau = cau.where(ConversationModel.department_id == department_id)

        ket_qua = await self._session.execute(cau)
        return Decimal(int(ket_qua.scalar_one()))

    async def _phut_phan_hoi_tb(
        self,
        period: KpiPeriod,
        user_id: UUID | None = None,
        department_id: UUID | None = None,
    ) -> Decimal | None:
        """Thời gian phản hồi trung bình (PHÚT) trong kỳ.

        Mỗi hội thoại: giây từ tin INBOUND đầu tới tin OUTBOUND đầu. Gắn kỳ theo
        NGÀY của tin OUTBOUND đầu (event-time, khớp #5). Với KPI cấp nhân viên, quy
        cho NGƯỜI gửi tin OUTBOUND đầu (người phản hồi); cấp phòng thì theo phòng
        hội thoại. Người gửi tin đầu lấy ``array_agg(... ORDER BY created_at)[1]``
        (Postgres không có ``min(uuid)``). Trả trung bình phút (làm tròn 0.1);
        ``None`` khi chưa có mẫu nào (progress hiển thị "chưa tính được").
        """
        dau, het = _khoang_ky(period)
        m_in = func.min(MessageModel.created_at).filter(MessageModel.direction == _INBOUND)
        m_out = func.min(MessageModel.created_at).filter(MessageModel.direction == _OUTBOUND)
        out_user = func.array_agg(
            aggregate_order_by(MessageModel.sender_user_id, MessageModel.created_at)
        ).filter(MessageModel.direction == _OUTBOUND)[1]
        sub = (
            select(
                MessageModel.conversation_id.label("cid"),
                m_in.label("in_dau"),
                m_out.label("out_dau"),
                out_user.label("out_user"),
            )
            .group_by(MessageModel.conversation_id)
            .subquery()
        )
        giay = cast(
            func.extract("epoch", sub.c.out_dau) - func.extract("epoch", sub.c.in_dau),
            Integer,
        )
        cau = (
            select(giay)
            .select_from(sub)
            .join(ConversationModel, ConversationModel.id == sub.c.cid)
            .where(
                sub.c.in_dau.isnot(None),
                sub.c.out_dau.isnot(None),
                sub.c.out_dau >= dau,
                sub.c.out_dau < het,
                giay >= 0,
            )
        )
        if user_id is not None:
            cau = cau.where(sub.c.out_user == user_id)
        if department_id is not None:
            cau = cau.where(ConversationModel.department_id == department_id)

        giay_list = [int(g) for (g,) in await self._session.execute(cau) if g is not None]
        if not giay_list:
            return None
        phut_tb = Decimal(sum(giay_list)) / Decimal(len(giay_list)) / Decimal(60)
        return phut_tb.quantize(Decimal("0.1"))
