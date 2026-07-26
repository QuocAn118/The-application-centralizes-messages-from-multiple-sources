"""Value object cho KPI: loại chỉ số, đối tượng áp dụng, và kỳ (tháng)."""

from dataclasses import dataclass
from enum import StrEnum

from src.shared.domain.exceptions import DomainError


class KpiMetricType(StrEnum):
    """Loại chỉ số đo được của một nhân viên/phòng ban.

    Giá trị **thực đạt** của các chỉ số này lấy từ nguồn hiệu suất (Inbox) qua
    port, không nhập tay. Danh sách mở rộng được: thêm chỉ số mới chỉ là thêm
    một giá trị ở đây kèm cách tính tương ứng ở nguồn hiệu suất.
    """

    CONVERSATIONS_CLOSED = "CONVERSATIONS_CLOSED"
    AVG_RESPONSE_MINUTES = "AVG_RESPONSE_MINUTES"


class KpiSubjectType(StrEnum):
    """Mục tiêu KPI áp cho một nhân viên hay cho cả một phòng ban."""

    USER = "USER"
    DEPARTMENT = "DEPARTMENT"


class InvalidKpiPeriodError(DomainError):
    """Kỳ KPI không hợp lệ (năm/tháng ngoài khoảng)."""

    def __init__(self) -> None:
        super().__init__(
            "Kỳ KPI không hợp lệ: tháng phải từ 1 đến 12 và năm phải dương.",
            code="INVALID_KPI_PERIOD",
        )


@dataclass(frozen=True)
class KpiPeriod:
    """Một kỳ báo cáo KPI, tính theo tháng.

    Mục tiêu KPI đặt theo tháng (đề bài nói "mục tiêu hàng tháng"). Giữ ở dạng
    (năm, tháng) thay vì một khoảng ngày để so khớp và lưu trữ đơn giản; việc
    quy đổi ra khoảng thời gian cụ thể để hỏi nguồn hiệu suất là việc của use
    case, không phải của value object này.
    """

    year: int
    month: int

    def __post_init__(self) -> None:
        if self.year <= 0 or not (1 <= self.month <= 12):
            raise InvalidKpiPeriodError
