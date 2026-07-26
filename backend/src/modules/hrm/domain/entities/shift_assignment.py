"""Entity phân ca — gán một mẫu ca cho một nhân viên vào một ngày cụ thể."""

from dataclasses import dataclass
from datetime import date, datetime, time
from uuid import UUID

from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import BusinessRuleViolationError


class PastShiftDateError(BusinessRuleViolationError):
    """Không phân ca cho một ngày đã qua."""

    def __init__(self) -> None:
        super().__init__(
            "Không thể phân ca cho một ngày trong quá khứ.",
            code="PAST_SHIFT_DATE",
        )


class ShiftAssignmentStatus:
    """Trạng thái một buổi phân ca. Chuỗi hằng, không cần enum riêng ở #4."""

    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


@dataclass(eq=False, kw_only=True)
class ShiftAssignment(AggregateRoot):
    """Một buổi làm thật: nhân viên ``user_id`` làm ca ``shift_id`` ngày ``work_date``.

    Giữ luôn khung giờ (``start_time``/``end_time``) chụp từ mẫu ca lúc phân, để
    kiểm chồng ca không phải nạp lại Shift và để lịch sử không đổi khi mẫu ca
    sau này bị sửa. ``user_id`` là tham chiếu UUID sang identity — không khoá
    ngoại, giữ module hrm độc lập.

    Chấm công thực tế (check-in/out) không thuộc #4; buổi phân ca chỉ có hai
    trạng thái: đang hiệu lực hoặc đã huỷ.
    """

    shift_id: UUID
    user_id: UUID
    department_id: UUID
    work_date: date
    start_time: time
    end_time: time
    created_at: datetime
    updated_at: datetime
    status: str = ShiftAssignmentStatus.ACTIVE

    @classmethod
    def assign(
        cls,
        shift_id: UUID,
        user_id: UUID,
        department_id: UUID,
        work_date: date,
        start_time: time,
        end_time: time,
        now: datetime,
    ) -> "ShiftAssignment":
        """Phân một buổi ca cho nhân viên. Từ chối nếu ngày đã qua."""
        if work_date < now.date():
            raise PastShiftDateError
        return cls(
            shift_id=shift_id,
            user_id=user_id,
            department_id=department_id,
            work_date=work_date,
            start_time=start_time,
            end_time=end_time,
            status=ShiftAssignmentStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

    def cancel(self, now: datetime) -> None:
        """Huỷ một buổi phân ca."""
        self.status = ShiftAssignmentStatus.CANCELLED
        self.updated_at = now

    @property
    def is_active(self) -> bool:
        return self.status == ShiftAssignmentStatus.ACTIVE

    def overlaps(self, other: "ShiftAssignment") -> bool:
        """Hai buổi phân ca có chồng khung giờ trong cùng một ngày không.

        Chỉ tính các buổi còn hiệu lực và của cùng một nhân viên: nền tảng chống
        một người bị xếp hai ca giẫm giờ. Hai khoảng ``[a_start, a_end)`` và
        ``[b_start, b_end)`` chồng nhau khi ``a_start < b_end`` và ``b_start < a_end``.
        """
        if not (self.is_active and other.is_active):
            return False
        if self.user_id != other.user_id or self.work_date != other.work_date:
            return False
        return self.start_time < other.end_time and other.start_time < self.end_time
