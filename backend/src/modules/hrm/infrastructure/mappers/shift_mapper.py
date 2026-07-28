"""Chuyển đổi giữa ORM model và domain entity của mẫu ca."""

from src.modules.hrm.domain.entities.shift import Shift
from src.modules.hrm.infrastructure.models.shift_model import ShiftModel


class ShiftMapper:
    """Cầu nối giữa bảng ``shifts`` và entity ``Shift``."""

    @staticmethod
    def to_domain(model: ShiftModel) -> Shift:
        return Shift(
            id=model.id,
            department_id=model.department_id,
            name=model.name,
            start_time=model.start_time,
            end_time=model.end_time,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: Shift) -> ShiftModel:
        return ShiftModel(
            id=entity.id,
            department_id=entity.department_id,
            name=entity.name,
            start_time=entity.start_time,
            end_time=entity.end_time,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def update_model(model: ShiftModel, entity: Shift) -> None:
        model.name = entity.name
        model.start_time = entity.start_time
        model.end_time = entity.end_time
        model.is_active = entity.is_active
        model.updated_at = entity.updated_at
