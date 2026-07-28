"""Cầu nối hrm → inbox: chỗ DUY NHẤT trong hrm được biết inbox tồn tại.

Implementation của port ``IPerformanceSource``. Nhờ ranh giới này, toàn bộ
domain/application/presentation của hrm không import inbox (import-linter xác
nhận); chỉ file infrastructure này truy vấn dữ liệu inbox để tính KPI thực đạt.

Đổi nguồn hiệu suất (thêm #2/#5) sau chỉ đụng file này, không đụng use case KPI.
"""

from calendar import monthrange
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
    """Nửa khoảng [đầu tháng, đầu tháng sau) theo UTC cho một kỳ."""
    dau = datetime(period.year, period.month, 1, tzinfo=UTC)
    so_ngay = monthrange(period.year, period.month)[1]
    cuoi = datetime(period.year, period.month, so_ngay, 23, 59, 59, 999999, tzinfo=UTC)
    return dau, cuoi


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
        """Số hội thoại đã đóng trong kỳ, gán cho một nhân viên hoặc thuộc một phòng.

        Dùng ``updated_at`` làm mốc đóng: hội thoại chuyển sang ``DA_DONG`` là
        lần cập nhật cuối. Đây là xấp xỉ đủ dùng cho #4; #5 có thể tính chính
        xác hơn bằng mốc đóng riêng — ghi nợ.
        """
        dau, cuoi = _khoang_ky(period)
        cau = (
            select(func.count())
            .select_from(ConversationModel)
            .where(
                ConversationModel.status == _DA_DONG,
                ConversationModel.updated_at >= dau,
                ConversationModel.updated_at <= cuoi,
            )
        )
        if user_id is not None:
            cau = cau.where(ConversationModel.assigned_user_id == user_id)
        if department_id is not None:
            cau = cau.where(ConversationModel.department_id == department_id)

        ket_qua = await self._session.execute(cau)
        return Decimal(int(ket_qua.scalar_one()))
