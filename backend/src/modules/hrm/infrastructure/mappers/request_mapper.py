"""Chuyển đổi giữa ORM model và domain entity của đơn từ."""

from src.modules.hrm.domain.entities.leave_request import LeaveRequest
from src.modules.hrm.domain.value_objects.request_kind import (
    RequestStatus,
    RequestType,
)
from src.modules.hrm.infrastructure.models.request_model import RequestModel


class RequestMapper:
    """Cầu nối giữa bảng ``requests`` và entity ``LeaveRequest``."""

    @staticmethod
    def to_domain(model: RequestModel) -> LeaveRequest:
        return LeaveRequest(
            id=model.id,
            requester_id=model.requester_id,
            department_id=model.department_id,
            request_type=RequestType(model.request_type),
            reason=model.reason,
            status=RequestStatus(model.status),
            leave_start=model.leave_start,
            leave_end=model.leave_end,
            decided_by=model.decided_by,
            decided_at=model.decided_at,
            decision_reason=model.decision_reason,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: LeaveRequest) -> RequestModel:
        return RequestModel(
            id=entity.id,
            requester_id=entity.requester_id,
            department_id=entity.department_id,
            request_type=entity.request_type.value,
            reason=entity.reason,
            status=entity.status.value,
            leave_start=entity.leave_start,
            leave_end=entity.leave_end,
            decided_by=entity.decided_by,
            decided_at=entity.decided_at,
            decision_reason=entity.decision_reason,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def update_model(model: RequestModel, entity: LeaveRequest) -> None:
        model.status = entity.status.value
        model.decided_by = entity.decided_by
        model.decided_at = entity.decided_at
        model.decision_reason = entity.decision_reason
        model.updated_at = entity.updated_at
