"""Chuyển đổi giữa ORM model và domain entity của mục tiêu KPI."""

from src.modules.hrm.domain.entities.kpi_target import KpiTarget
from src.modules.hrm.domain.value_objects.kpi import (
    KpiMetricType,
    KpiPeriod,
    KpiSubjectType,
)
from src.modules.hrm.infrastructure.models.kpi_target_model import KpiTargetModel


class KpiTargetMapper:
    """Cầu nối giữa bảng ``kpi_targets`` và entity ``KpiTarget``.

    Kỳ được tách thành hai cột ``period_year``/``period_month`` khi lưu và ghép
    lại thành value object ``KpiPeriod`` khi đọc.
    """

    @staticmethod
    def to_domain(model: KpiTargetModel) -> KpiTarget:
        return KpiTarget(
            id=model.id,
            subject_type=KpiSubjectType(model.subject_type),
            subject_id=model.subject_id,
            department_id=model.department_id,
            metric_type=KpiMetricType(model.metric_type),
            period=KpiPeriod(year=model.period_year, month=model.period_month),
            target_value=model.target_value,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: KpiTarget) -> KpiTargetModel:
        return KpiTargetModel(
            id=entity.id,
            subject_type=entity.subject_type.value,
            subject_id=entity.subject_id,
            department_id=entity.department_id,
            metric_type=entity.metric_type.value,
            period_year=entity.period.year,
            period_month=entity.period.month,
            target_value=entity.target_value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def update_model(model: KpiTargetModel, entity: KpiTarget) -> None:
        model.target_value = entity.target_value
        model.updated_at = entity.updated_at
