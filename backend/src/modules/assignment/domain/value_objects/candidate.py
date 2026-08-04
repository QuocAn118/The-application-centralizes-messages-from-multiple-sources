"""Value object mô tả một ứng viên nhận việc và kết cục một lần auto-assign.

``AgentCandidate`` gói đúng các tín hiệu bộ chọn cần, ở dạng trung lập với
identity/hrm/inbox — tầng infrastructure gom dữ liệu từ các module đó rồi dịch
sang kiểu này (giữ domain #3 độc lập).
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class AssignmentOutcome(StrEnum):
    """Kết cục một lần thử auto-assign một hội thoại.

    ``ASSIGNED``: đã chọn được nhân viên hợp lệ và gán thành công.
    ``QUEUED``: không có ai nhận được (không ai trong ca / phòng rỗng) → hội thoại
    nằm trong hàng đợi phòng, chờ.
    ``SKIPPED``: không cần gán (hội thoại đã có người / không ở trạng thái gán được).
    """

    ASSIGNED = "ASSIGNED"
    QUEUED = "QUEUED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class AgentCandidate:
    """Một nhân viên có thể nhận việc, kèm các tín hiệu để bộ chọn xếp hạng.

    - ``on_shift``: có buổi phân ca đang hiệu lực bao thời điểm xét (#4). Đây là
      điều kiện LỌC bắt buộc — ngoài ca bị loại trước mọi tiêu chí khác.
    - ``open_load``: số hội thoại ``DANG_MO`` nhân viên đang giữ (#1) — càng thấp
      càng ưu tiên (cân bằng tải).
    - ``kpi_percent``: phần trăm đạt KPI kỳ hiện tại (#4); ``None`` khi chưa có dữ
      liệu. Người dưới target (thấp hơn) được ưu tiên nhận thêm; ``None`` xem như
      "chưa đạt" (ưu tiên như thấp nhất).
    - ``last_assigned_at``: thời điểm gần nhất nhân viên được gán một hội thoại
      (#1); ``None`` = chưa từng. Dùng phá hoà round-robin (cũ nhất/None trước).
    """

    user_id: UUID
    on_shift: bool
    open_load: int
    kpi_percent: Decimal | None = None
    last_assigned_at: datetime | None = None


@dataclass(frozen=True)
class AssignmentEvent:
    """Một lần gán thành công một hội thoại cho một nhân viên — bản ghi lịch sử.

    Ghi khi (và chỉ khi) inbox chấp nhận gán (``AssignResult.ASSIGNED``). Đây là
    nguồn sự thật cho "được gán bao nhiêu lần" (khác ``conversations.assigned_user_id``
    chỉ giữ NGƯỜI CUỐI): một hội thoại có thể được gán lại nhiều lần, và #5 cần đếm
    đủ mọi lần để dựng ``assigned_count``.

    - ``department_id``: phòng của hội thoại tại thời điểm gán (có thể ``None`` nếu
      hội thoại chưa phân phòng — hiếm, vì auto-assign chạy sau khi đã có phòng).
    - ``assigned_at``: thời điểm gán (UTC-aware), do clock hệ thống cấp.
    """

    conversation_id: UUID
    user_id: UUID
    department_id: UUID | None
    assigned_at: datetime
