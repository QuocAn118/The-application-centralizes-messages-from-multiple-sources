"""Chuyển đổi giữa ORM model và domain entity của buổi phân ca."""

from src.modules.hrm.domain.entities.shift_assignment import ShiftAssignment
from src.modules.hrm.infrastructure.models.shift_assignment_model import (
    ShiftAssignmentModel,
)


class ShiftAssignmentMapper:
    """Cầu nối giữa bảng ``shift_assignments`` và entity ``ShiftAssignment``."""

    @staticmethod
    def to_domain(model: ShiftAssignmentModel) -> ShiftAssignment:
        return ShiftAssignment(
            id=model.id,
            shift_id=model.shift_id,
            user_id=model.user_id,
            department_id=model.department_id,
            work_date=model.work_date,
            start_time=model.start_time,
            end_time=model.end_time,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: ShiftAssignment) -> ShiftAssignmentModel:
        return ShiftAssignmentModel(
            id=entity.id,
            shift_id=entity.shift_id,
            user_id=entity.user_id,
            department_id=entity.department_id,
            work_date=entity.work_date,
            start_time=entity.start_time,
            end_time=entity.end_time,
            status=entity.status,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def update_model(model: ShiftAssignmentModel, entity: ShiftAssignment) -> None:
        model.status = entity.status
        model.updated_at = entity.updated_at
