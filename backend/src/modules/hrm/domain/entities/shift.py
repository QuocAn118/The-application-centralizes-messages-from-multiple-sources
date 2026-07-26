"""Entity ca làm việc — mẫu khung giờ của một phòng ban."""

from dataclasses import dataclass
from datetime import datetime, time
from uuid import UUID

from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import BusinessRuleViolationError


class InvalidShiftWindowError(BusinessRuleViolationError):
    """Giờ kết thúc ca phải sau giờ bắt đầu (ca không qua nửa đêm ở #4)."""

    def __init__(self) -> None:
        super().__init__(
            "Khung giờ ca không hợp lệ: giờ kết thúc phải sau giờ bắt đầu.",
            code="INVALID_SHIFT_WINDOW",
        )


class EmptyShiftNameError(BusinessRuleViolationError):
    """Tên ca không được rỗng."""

    def __init__(self) -> None:
        super().__init__(
            "Tên ca không được để trống.",
            code="EMPTY_SHIFT_NAME",
        )


@dataclass(eq=False, kw_only=True)
class Shift(AggregateRoot):
    """Một mẫu ca: tên + khung giờ trong ngày, thuộc một phòng ban.

    Đây là *khuôn*, không phải một buổi làm cụ thể — buổi làm thật là
    ``ShiftAssignment`` (gán ca này cho một nhân viên vào một ngày).

    ``department_id`` là tham chiếu UUID sang phòng ban của identity — cố ý
    không phải khoá ngoại, giữ module hrm độc lập. Ca không hỗ trợ qua nửa đêm
    ở #4: ``end_time`` phải lớn hơn ``start_time`` trong cùng một ngày.
    """

    department_id: UUID
    name: str
    start_time: time
    end_time: time
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    @staticmethod
    def _kiem_tra(name: str, start_time: time, end_time: time) -> str:
        ten = name.strip()
        if not ten:
            raise EmptyShiftNameError
        if end_time <= start_time:
            raise InvalidShiftWindowError
        return ten

    @classmethod
    def create(
        cls,
        department_id: UUID,
        name: str,
        start_time: time,
        end_time: time,
        now: datetime,
    ) -> "Shift":
        """Tạo một mẫu ca mới."""
        ten = cls._kiem_tra(name, start_time, end_time)
        return cls(
            department_id=department_id,
            name=ten,
            start_time=start_time,
            end_time=end_time,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    def update_window(self, name: str, start_time: time, end_time: time, now: datetime) -> None:
        """Đổi tên và/hoặc khung giờ, giữ nguyên bất biến giờ hợp lệ."""
        self.name = self._kiem_tra(name, start_time, end_time)
        self.start_time = start_time
        self.end_time = end_time
        self.updated_at = now

    def deactivate(self, now: datetime) -> None:
        self.is_active = False
        self.updated_at = now
