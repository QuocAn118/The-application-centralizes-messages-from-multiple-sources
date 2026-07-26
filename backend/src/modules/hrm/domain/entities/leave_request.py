"""Entity đơn từ nội bộ — dùng cho mọi loại đơn, với máy trạng thái phê duyệt."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from src.modules.hrm.domain.value_objects.request_kind import (
    RequestStatus,
    RequestType,
)
from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import BusinessRuleViolationError


class MissingLeavePeriodError(BusinessRuleViolationError):
    """Đơn nghỉ phép phải có khoảng thời gian nghỉ."""

    def __init__(self) -> None:
        super().__init__(
            "Đơn nghỉ phép phải khai khoảng thời gian nghỉ.",
            code="MISSING_LEAVE_PERIOD",
        )


class InvalidLeavePeriodError(BusinessRuleViolationError):
    """Khoảng thời gian nghỉ không hợp lệ (ngày kết thúc trước ngày bắt đầu, hoặc ở quá khứ)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INVALID_LEAVE_PERIOD")


class EmptyReasonError(BusinessRuleViolationError):
    """Đơn phải có lý do."""

    def __init__(self) -> None:
        super().__init__(
            "Đơn phải khai lý do.",
            code="EMPTY_REQUEST_REASON",
        )


class RequestNotPendingError(BusinessRuleViolationError):
    """Chỉ đơn đang chờ duyệt mới được duyệt/từ chối/thu hồi."""

    def __init__(self) -> None:
        super().__init__(
            "Đơn không còn ở trạng thái chờ duyệt.",
            code="REQUEST_NOT_PENDING",
        )


class MissingRejectionReasonError(BusinessRuleViolationError):
    """Từ chối đơn bắt buộc kèm lý do."""

    def __init__(self) -> None:
        super().__init__(
            "Từ chối đơn phải kèm lý do.",
            code="MISSING_REJECTION_REASON",
        )


@dataclass(eq=False, kw_only=True)
class LeaveRequest(AggregateRoot):
    """Một đơn từ nội bộ do nhân viên gửi, chờ người có quyền duyệt.

    Tên lớp giữ ``LeaveRequest`` cho ngắn gọn nhưng phục vụ mọi ``RequestType``
    (nghỉ phép, tăng lương, khác). Chỉ ``NGHI_PHEP`` bắt buộc có khoảng thời
    gian ``leave_start``/``leave_end``.

    ``requester_id``/``department_id``/``decided_by`` là UUID thuần tham chiếu
    identity — không khoá ngoại, giữ module hrm độc lập. ``department_id`` được
    chụp lại lúc gửi để định tuyến người duyệt và giữ lịch sử ổn định.

    Đơn ở trạng thái cuối (``DA_DUYET``/``TU_CHOI``/``DA_HUY``) là bất biến:
    mọi thao tác duyệt/từ chối/thu hồi đều đòi trạng thái ``CHO_DUYET``.
    """

    requester_id: UUID
    department_id: UUID
    request_type: RequestType
    reason: str
    status: RequestStatus
    created_at: datetime
    updated_at: datetime
    leave_start: date | None = None
    leave_end: date | None = None
    decided_by: UUID | None = None
    decided_at: datetime | None = None
    decision_reason: str | None = None

    @classmethod
    def submit(
        cls,
        requester_id: UUID,
        department_id: UUID,
        request_type: RequestType,
        reason: str,
        now: datetime,
        leave_start: date | None = None,
        leave_end: date | None = None,
    ) -> "LeaveRequest":
        """Gửi một đơn mới. Validate theo loại đơn."""
        ly_do = reason.strip()
        if not ly_do:
            raise EmptyReasonError

        if request_type is RequestType.NGHI_PHEP:
            if leave_start is None or leave_end is None:
                raise MissingLeavePeriodError
            if leave_end < leave_start:
                raise InvalidLeavePeriodError("Ngày kết thúc nghỉ không được trước ngày bắt đầu.")
            if leave_start < now.date():
                raise InvalidLeavePeriodError("Không thể xin nghỉ cho một ngày đã qua.")
        else:
            # Loại đơn khác không mang khoảng thời gian — bỏ nếu lỡ truyền vào.
            leave_start = None
            leave_end = None

        return cls(
            requester_id=requester_id,
            department_id=department_id,
            request_type=request_type,
            reason=ly_do,
            leave_start=leave_start,
            leave_end=leave_end,
            status=RequestStatus.CHO_DUYET,
            created_at=now,
            updated_at=now,
        )

    def approve(self, approver_id: UUID, now: datetime) -> None:
        """Người có quyền duyệt đơn. Quyền 'ai được duyệt' kiểm ở use case."""
        if self.status is not RequestStatus.CHO_DUYET:
            raise RequestNotPendingError
        self.status = RequestStatus.DA_DUYET
        self.decided_by = approver_id
        self.decided_at = now
        self.updated_at = now

    def reject(self, approver_id: UUID, reason: str, now: datetime) -> None:
        """Từ chối đơn, bắt buộc kèm lý do."""
        if self.status is not RequestStatus.CHO_DUYET:
            raise RequestNotPendingError
        ly_do = reason.strip()
        if not ly_do:
            raise MissingRejectionReasonError
        self.status = RequestStatus.TU_CHOI
        self.decided_by = approver_id
        self.decided_at = now
        self.decision_reason = ly_do
        self.updated_at = now

    def cancel(self, now: datetime) -> None:
        """Người gửi thu hồi đơn khi chưa ai duyệt. Quyền 'chủ đơn' kiểm ở use case."""
        if self.status is not RequestStatus.CHO_DUYET:
            raise RequestNotPendingError
        self.status = RequestStatus.DA_HUY
        self.updated_at = now
