"""Cầu nối hrm → inbox: chỗ DUY NHẤT trong hrm được biết inbox tồn tại.

Implementation của port ``IPerformanceSource``. Nhờ ranh giới này, toàn bộ
domain/application/presentation của hrm không import inbox (import-linter xác
nhận); chỉ file infrastructure này truy vấn dữ liệu inbox để tính KPI thực đạt.

Đổi nguồn hiệu suất (thêm #2/#5) sau chỉ đụng file này, không đụng use case KPI.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.hrm.domain.value_objects.kpi import KpiMetricType, KpiPeriod
from src.modules.inbox.infrastructure.models.conversation_model import ConversationModel

# Trạng thái "đã xử lý xong" của hội thoại inbox — hằng chuỗi để không import
# enum của inbox (chỉ cần giá trị, không cần kiểu).
_DA_DONG = "DA_DONG"


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
        # AVG_RESPONSE_MINUTES cần ghép cặp inbound→outbound đầu tiên — chưa làm
        # ở #4, trả None (chưa có dữ liệu) để progress hiển thị "chưa tính được".
        return None

    async def get_metric_for_department(
        self, department_id: UUID, metric_type: KpiMetricType, period: KpiPeriod
    ) -> Decimal | None:
        if metric_type is KpiMetricType.CONVERSATIONS_CLOSED:
            return await self._dem_hoi_thoai_dong(period, department_id=department_id)
        return None

    async def _dem_hoi_thoai_dong(
        self,
        period: KpiPeriod,
        user_id: UUID | None = None,
        department_id: UUID | None = None,
    ) -> Decimal:
        """Số hội thoại đang ``DA_DONG`` được cập nhật lần cuối trong kỳ, gán cho
        một nhân viên hoặc thuộc một phòng.

        NỢ ĐÃ BIẾT (spec §10): dùng ``updated_at`` làm xấp xỉ "mốc đóng" vì bảng
        ``conversations`` của inbox không có cột ``closed_at`` riêng, và inbox
        (#1) đã đóng băng schema. Xấp xỉ này lệch trong hai trường hợp: hội thoại
        đóng trong kỳ rồi khách nhắn lại (chuyển ``DANG_MO``) sẽ không được đếm;
        hội thoại đóng kỳ trước nhưng bị cập nhật lại trong kỳ này (vẫn
        ``DA_DONG``) sẽ bị đếm nhầm sang kỳ này. Tính chính xác cần thêm
        ``closed_at`` ở inbox — để #5 Analytics làm.
        """
        dau, het = _khoang_ky(period)
        cau = (
            select(func.count())
            .select_from(ConversationModel)
            .where(
                ConversationModel.status == _DA_DONG,
                ConversationModel.updated_at >= dau,
                ConversationModel.updated_at < het,
            )
        )
        if user_id is not None:
            cau = cau.where(ConversationModel.assigned_user_id == user_id)
        if department_id is not None:
            cau = cau.where(ConversationModel.department_id == department_id)

        ket_qua = await self._session.execute(cau)
        return Decimal(int(ket_qua.scalar_one()))
