"""Cầu nối analytics → #4 (đọc): ca làm + đơn từ, đọc THẲNG bảng #4.

Implementation ``IWorkforceStatsSource`` + ``IRequestStatsSource``. Dữ liệu #4 vốn
đã tổng hợp nên #5 GROUP BY tại query time thay vì rollup lại (chốt với user).
Đây là chỗ analytics.infrastructure được phép chạm #4.

NỢ KPI (kế thừa #3): ``kpi_percent``/``period`` để ``None`` — tính KPI đủ nghĩa
cần chốt chỉ số/kỳ/nguồn hiệu suất (quyết định nghiệp vụ chưa có, ``GetKpiProgress``
#4 đòi metric_type/period cụ thể). Bản đầu báo cáo ca làm (số ca + giờ công) chính
xác; KPI nối khi nghiệp vụ chốt chỉ số chuẩn.
"""

from uuid import UUID

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.analytics.domain.ports import RequestRow, WorkforceRow
from src.modules.analytics.domain.value_objects.metrics import DateRange
from src.modules.hrm.infrastructure.models.request_model import RequestModel
from src.modules.hrm.infrastructure.models.shift_assignment_model import (
    ShiftAssignmentModel,
)

# Trạng thái đơn đã "quyết" (có decided_at) để tính thời gian duyệt.
_DA_QUYET = ("DA_DUYET", "TU_CHOI")


class HrmStatsSource:
    """Đọc ca làm + đơn từ thẳng từ #4."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def workforce_rows(
        self, khoang: DateRange, department_ids: tuple[UUID, ...] | None
    ) -> tuple[WorkforceRow, ...]:
        """Số ca + giờ công theo nhân viên trong khoảng (lọc theo ``work_date``).

        ``worked_seconds`` = tổng ``(end_time - start_time)`` các ca ACTIVE. KPI để
        ``None`` (nợ). Nhóm theo ``(user_id, department_id)``.
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

        ket_qua = await self._session.execute(cau)
        return tuple(
            WorkforceRow(
                user_id=r.user_id,
                department_id=r.department_id,
                shift_count=r.shift_count,
                worked_seconds=int(r.worked_seconds),
                kpi_percent=None,  # NỢ: xem docstring module.
                period=None,
            )
            for r in ket_qua
        )

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
