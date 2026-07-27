"""Interface repository cho KpiTarget (mục tiêu KPI)."""

from typing import Protocol
from uuid import UUID

from src.modules.hrm.domain.entities.kpi_target import KpiTarget
from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)


class IKpiTargetRepository(Protocol):
    """Truy xuất mục tiêu KPI."""

    async def get_by_id(self, target_id: UUID) -> KpiTarget | None: ...

    async def get_for(
        self,
        subject_type: KpiSubjectType,
        subject_id: UUID,
        metric_type: KpiMetricType,
        period: KpiPeriod,
    ) -> KpiTarget | None:
        """Mục tiêu đã đặt cho đúng (đối tượng, chỉ số, kỳ), nếu có.

        ``SetKpiTarget`` dùng để quyết định tạo mới hay cập nhật — bảng có ràng
        buộc duy nhất trên bộ khoá này.
        """
        ...

    async def add(self, target: KpiTarget) -> None: ...

    async def update(self, target: KpiTarget) -> None: ...

    async def list_in_scope(
        self,
        department_ids: list[UUID] | None,
        subject_id: UUID | None = None,
        period: KpiPeriod | None = None,
    ) -> list[KpiTarget]:
        """Liệt kê mục tiêu theo phạm vi.

        ``department_ids`` lọc theo phòng của mục tiêu (Manager xem cả mục tiêu
        cấp phòng lẫn cấp nhân viên trong phòng mình); ``None`` nghĩa là không
        giới hạn phòng (Admin). ``subject_id`` siết thêm về đúng một đối tượng
        (Staff chỉ xem mục tiêu áp cho chính mình). Kỳ tuỳ chọn.
        """
        ...
