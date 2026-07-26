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

    async def list_for_subjects(
        self,
        subject_ids: list[UUID] | None,
        period: KpiPeriod | None = None,
    ) -> list[KpiTarget]:
        """Liệt kê mục tiêu theo phạm vi đối tượng (nhân viên/phòng cho phép).

        ``subject_ids=None`` nghĩa là không giới hạn (Admin). Kỳ tuỳ chọn.
        """
        ...
