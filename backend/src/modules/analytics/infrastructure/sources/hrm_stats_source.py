"""Cầu nối analytics → #4 (đọc): ca làm + đơn từ, đọc THẲNG bảng #4.

Implementation ``IWorkforceStatsSource`` + ``IRequestStatsSource``. Dữ liệu #4 vốn
đã tổng hợp nên #5 GROUP BY tại query time thay vì rollup lại (chốt với user).
Đây là chỗ analytics.infrastructure được phép chạm #4.

KPI (chốt 2026-08-04): ``kpi_percent`` = % hoàn thành ``CONVERSATIONS_CLOSED`` cho
**tháng của ``to_date``** (kỳ chuẩn KPI theo tháng; báo cáo khoảng nhiều tháng lấy
kỳ ở cuối khoảng — mốc KPI hiện hành tại cuối kỳ báo cáo). ``period`` ghi rõ
``YYYY-MM`` để không nhập nhằng. ``None`` khi nhân viên chưa đặt target tháng đó.
Ghép mục tiêu (#4 KpiTarget) với thực đạt (#4 nguồn hiệu suất Inbox) qua
``tinh_phan_tram_kpi`` — dùng chung công thức chiều chỉ số với #3/#4.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.analytics.domain.ports import RequestRow, WorkforceRow
from src.modules.analytics.domain.value_objects.metrics import DateRange
from src.modules.hrm.domain.services.kpi_achievement import tinh_phan_tram_kpi
from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.modules.hrm.infrastructure.models.request_model import RequestModel
from src.modules.hrm.infrastructure.models.shift_assignment_model import (
    ShiftAssignmentModel,
)
from src.modules.hrm.infrastructure.performance.inbox_performance_source import (
    InboxPerformanceSource,
)
from src.modules.hrm.infrastructure.repositories.kpi_target_repository import (
    SqlAlchemyKpiTargetRepository,
)

# Trạng thái đơn đã "quyết" (có decided_at) để tính thời gian duyệt.
_DA_QUYET = ("DA_DUYET", "TU_CHOI")

# Chỉ số KPI báo cáo (đồng bộ với định tuyến #3): số hội thoại đóng.
_METRIC_KPI = KpiMetricType.CONVERSATIONS_CLOSED


class HrmStatsSource:
    """Đọc ca làm + đơn từ thẳng từ #4."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._target_repo = SqlAlchemyKpiTargetRepository(session)
        self._performance = InboxPerformanceSource(session)

    async def workforce_rows(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[WorkforceRow, ...]:
        """Số ca + giờ công theo nhân viên trong khoảng (lọc theo ``work_date``).

        ``worked_seconds`` = tổng ``(end_time - start_time)`` các ca ACTIVE. Nhóm
        theo ``(user_id, department_id)``. ``kpi_percent`` = % CONVERSATIONS_CLOSED
        cho THÁNG của ``to_date`` (kỳ ở cuối khoảng báo cáo), ``None`` nếu chưa có
        target tháng đó.
        """
        giay_ca = cast(
            func.extract("epoch", ShiftAssignmentModel.end_time)
            - func.extract("epoch", ShiftAssignmentModel.start_time),
            Integer,
        )
        cau = (
            select(
                ShiftAssignmentModel.user_id,
                ShiftAssignmentModel.department_id,
                func.count().label("shift_count"),
                func.coalesce(func.sum(giay_ca), 0).label("worked_seconds"),
            )
            .where(
                ShiftAssignmentModel.work_date >= khoang.from_date,
                ShiftAssignmentModel.work_date <= khoang.to_date,
                ShiftAssignmentModel.status == "ACTIVE",
            )
            .group_by(ShiftAssignmentModel.user_id, ShiftAssignmentModel.department_id)
            .order_by(ShiftAssignmentModel.user_id)
        )
        if department_ids is not None:
            cau = cau.where(ShiftAssignmentModel.department_id.in_(department_ids))

        ket_qua = list(await self._session.execute(cau))

        # KPI cho tháng của to_date. Lấy mọi target CONVERSATIONS_CLOSED cấp nhân
        # viên trong phạm vi phòng một lần, index theo user_id.
        ky = KpiPeriod(year=khoang.to_date.year, month=khoang.to_date.month)
        dept_filter = list(department_ids) if department_ids is not None else None
        muc_tieu = {
            t.subject_id: t.target_value
            for t in await self._target_repo.list_in_scope(dept_filter, period=ky)
            if t.subject_type is KpiSubjectType.USER and t.metric_type is _METRIC_KPI
        }
        ky_str = f"{ky.year:04d}-{ky.month:02d}"

        rows: list[WorkforceRow] = []
        for r in ket_qua:
            target = muc_tieu.get(r.user_id)
            kpi: Decimal | None = None
            if target is not None:
                actual = await self._performance.get_metric_for_user(r.user_id, _METRIC_KPI, ky)
                kpi = tinh_phan_tram_kpi(_METRIC_KPI, target, actual)
            rows.append(
                WorkforceRow(
                    user_id=r.user_id,
                    department_id=r.department_id,
                    shift_count=r.shift_count,
                    worked_seconds=int(r.worked_seconds),
                    kpi_percent=kpi,
                    period=ky_str if target is not None else None,
                )
            )
        return tuple(rows)

    async def request_rows(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[RequestRow, ...]:
        """Đơn theo ``(phòng, loại, trạng thái)``; thời gian duyệt cho đơn đã quyết.

        Lọc theo ngày tạo đơn (``created_at`` quy về ngày). ``sum_decision_seconds``/
        ``decided_samples`` chỉ cộng đơn đã quyết (có ``decided_at``) để tính trung
        bình thời gian duyệt đúng.
        """
        giay_duyet = cast(
            func.extract("epoch", RequestModel.decided_at)
            - func.extract("epoch", RequestModel.created_at),
            Integer,
        )
        da_quyet = RequestModel.status.in_(_DA_QUYET)
        cau = (
            select(
                RequestModel.department_id,
                RequestModel.request_type,
                RequestModel.status,
                func.count().label("so_luong"),
                func.coalesce(func.sum(giay_duyet).filter(da_quyet), 0).label(
                    "sum_decision_seconds"
                ),
                func.coalesce(func.count().filter(da_quyet), 0).label("decided_samples"),
            )
            .where(
                func.date(RequestModel.created_at) >= khoang.from_date,
                func.date(RequestModel.created_at) <= khoang.to_date,
            )
            .group_by(
                RequestModel.department_id,
                RequestModel.request_type,
                RequestModel.status,
            )
            .order_by(RequestModel.department_id, RequestModel.request_type, RequestModel.status)
        )
        if department_ids is not None:
            cau = cau.where(RequestModel.department_id.in_(department_ids))

        ket_qua = await self._session.execute(cau)
        return tuple(
            RequestRow(
                department_id=r.department_id,
                request_type=r.request_type,
                status=r.status,
                count=r.so_luong,
                sum_decision_seconds=int(r.sum_decision_seconds),
                decided_samples=r.decided_samples,
            )
            for r in ket_qua
        )
