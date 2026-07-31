"""Value object số liệu báo cáo — trung lập, không I/O, không biết module nguồn.

Tầng infrastructure gom dữ liệu từ #1/#4 rồi dịch sang các kiểu này; domain và
use case chỉ làm việc với chúng. Mọi VO ``frozen`` (bất biến). Trung bình được
lưu dưới dạng **tổng + số mẫu** (``sum``/``samples``) chứ không phải "trung bình
sẵn", để cộng dồn nhiều ngày mà vẫn đúng (xem ``domain/services/aggregation``).
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from src.shared.application.exceptions import ApplicationError


@dataclass(frozen=True)
class DateRange:
    """Khoảng ngày báo cáo, đóng hai đầu (``from_date`` ≤ ``to_date``).

    Ngày ở đây là **ngày nghiệp vụ địa phương** (đã quy đổi theo ``app_timezone``),
    không phải ngày UTC — báo cáo cắt theo ngày làm việc VN (RB-5).
    """

    from_date: date
    to_date: date

    def __post_init__(self) -> None:
        if self.from_date > self.to_date:
            raise ApplicationError(
                "Khoảng ngày không hợp lệ: from_date phải nhỏ hơn hoặc bằng to_date.",
                code="ANALYTICS_INVALID_DATE_RANGE",
            )


@dataclass(frozen=True)
class DailyConversationMetric:
    """Một dòng rollup khối lượng của một ngày theo phòng theo kênh (#1).

    Khoá tự nhiên: ``(work_date, department_id, channel_platform)``.
    ``department_id`` có thể ``None`` (hội thoại chưa phân phòng — CHO_PHAN).
    """

    work_date: date
    department_id: UUID | None
    channel_platform: str
    inbound_count: int = 0
    outbound_count: int = 0
    opened_count: int = 0
    closed_count: int = 0


@dataclass(frozen=True)
class DailyAgentMetric:
    """Một dòng rollup hiệu suất của một ngày theo nhân viên (#1 + #3).

    Khoá tự nhiên: ``(work_date, user_id)``. Thời gian phản hồi/đóng lưu **tổng
    giây + số mẫu** để tính trung bình chuẩn khi gộp nhiều ngày; hội thoại chưa
    phản hồi/chưa đóng không vào mẫu (không kéo trung bình sai).
    """

    work_date: date
    user_id: UUID
    handled_count: int = 0
    assigned_count: int = 0
    sum_first_response_seconds: int = 0
    first_response_samples: int = 0
    sum_resolution_seconds: int = 0
    resolution_samples: int = 0


@dataclass(frozen=True)
class ConversationVolume:
    """Số liệu khối lượng đã gộp cho một chiều trình bày (một phòng/kênh/ngày).

    Kết quả API — không có khoá thời gian cố định; caller quyết định nhóm theo gì.
    """

    inbound_count: int
    outbound_count: int
    opened_count: int
    closed_count: int


@dataclass(frozen=True)
class AgentPerformance:
    """Hiệu suất một nhân viên đã gộp trong khoảng báo cáo.

    ``avg_first_response_seconds``/``avg_resolution_seconds`` là ``None`` khi chưa
    có mẫu nào (chưa phản hồi/đóng hội thoại nào) — không suy ra 0 (0 nghĩa là
    "phản hồi tức thì", khác hẳn "không có dữ liệu").
    """

    user_id: UUID
    handled_count: int
    assigned_count: int
    avg_first_response_seconds: float | None
    avg_resolution_seconds: float | None
