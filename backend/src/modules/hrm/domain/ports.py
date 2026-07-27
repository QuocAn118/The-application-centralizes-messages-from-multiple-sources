"""Cổng (port) mà tầng application của hrm phụ thuộc.

Mọi thứ ở đây là interface: implementation nằm ở tầng infrastructure. Nhờ vậy
domain và use case không biết identity, inbox, hay WebSocket tồn tại — chúng
chỉ biết các hợp đồng này. Đây là ranh giới giữ module hrm độc lập.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from src.modules.hrm.domain.value_objects.kpi import KpiMetricType, KpiPeriod


@dataclass(frozen=True)
class AgentInfo:
    """Thông tin tối thiểu về một nhân viên, lấy từ module identity."""

    user_id: UUID
    department_id: UUID | None
    role: str
    is_active: bool


class IWorkforceDirectory(Protocol):
    """Hỏi module identity gián tiếp, không import identity vào hrm.

    Chỉ implementation ở infrastructure mới biết identity tồn tại. Cùng hình
    dạng với port của inbox nhưng khai báo riêng — hai module dùng chung *ý
    tưởng*, không chung *kiểu*, để không nối phụ thuộc.

    ``get_manager_of_department`` phục vụ định tuyến người duyệt đơn: đơn của
    Staff về Manager phòng đó.
    """

    async def get_agent(self, user_id: UUID) -> AgentInfo | None: ...

    async def department_exists_active(self, department_id: UUID) -> bool: ...

    async def get_manager_of_department(self, department_id: UUID) -> AgentInfo | None: ...


class IPerformanceSource(Protocol):
    """Cung cấp giá trị KPI **thực đạt** của một đối tượng trong một kỳ.

    Implementation ở infrastructure truy vấn dữ liệu inbox (số hội thoại đóng,
    thời gian phản hồi). Đây là ranh giới giữ hrm độc lập với inbox: use case
    KPI chỉ biết port này, không biết inbox tồn tại. Đổi nguồn (thêm #2/#5) sau
    không đụng use case.

    Trả ``None`` khi không có dữ liệu cho đối tượng/kỳ đó (khác với 0 = có dữ
    liệu và bằng không).
    """

    async def get_metric_for_user(
        self, user_id: UUID, metric_type: KpiMetricType, period: KpiPeriod
    ) -> Decimal | None: ...

    async def get_metric_for_department(
        self, department_id: UUID, metric_type: KpiMetricType, period: KpiPeriod
    ) -> Decimal | None: ...


class INotifier(Protocol):
    """Đẩy tín hiệu 'đơn có thay đổi' tới người liên quan (người gửi/người duyệt).

    Chỉ gửi tín hiệu (request_id + loại thay đổi), không gửi nội dung — client
    tự gọi REST để lấy. Cố ý trung lập với hạ tầng WebSocket cụ thể để không
    nối hrm vào inbox.
    """

    async def notify_request_changed(
        self,
        request_id: UUID,
        recipient_user_id: UUID,
        change: str,
    ) -> None: ...


# Loại thay đổi đơn từ, để use case và notifier dùng chung một tên.
CHANGE_REQUEST_SUBMITTED = "request_submitted"
CHANGE_REQUEST_DECIDED = "request_decided"
