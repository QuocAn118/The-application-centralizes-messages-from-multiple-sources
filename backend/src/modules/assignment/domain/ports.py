"""Cổng (port) mà tầng application của assignment phụ thuộc.

Mọi thứ ở đây là interface: implementation nằm ở tầng infrastructure. Nhờ vậy
domain và use case không biết inbox, hrm, identity hay keyword tồn tại — chỉ biết
các hợp đồng này. Đây là ranh giới giữ module assignment độc lập.
"""

from typing import Protocol
from uuid import UUID

from src.modules.assignment.domain.value_objects.candidate import AgentCandidate


class IAgentPool(Protocol):
    """Gom danh sách ứng viên của một phòng kèm tín hiệu xếp hạng.

    Implementation (infrastructure) đọc identity (nhân viên phòng), #4 (ca làm,
    KPI) và #1 (tải hội thoại đang giữ, mốc gán gần nhất) rồi dịch mỗi người
    thành ``AgentCandidate`` trung lập. Chỉ trả nhân viên active của phòng.
    """

    async def candidates_for_department(
        self, department_id: UUID
    ) -> tuple[AgentCandidate, ...]: ...


class IConversationAssigner(Protocol):
    """Gán một hội thoại cho một nhân viên — chỗ DUY NHẤT assignment tác động ngược
    vào inbox.

    Implementation gọi use case gán-nhân-viên chính thống của #1 với actor hệ
    thống, nên máy trạng thái/phân quyền/realtime của inbox giữ nguyên. Trả
    ``True`` nếu gán thành công; ``False`` nếu #1 từ chối (hội thoại đã có người,
    không còn ``DANG_MO``, …) — auto-assign thất bại không được làm hỏng luồng gọi.
    """

    async def assign_to_agent(self, conversation_id: UUID, user_id: UUID) -> bool: ...


class IWaitingQueue(Protocol):
    """Đọc hàng đợi của một phòng: hội thoại ``DANG_MO`` chưa có người nhận.

    Trả danh sách ``conversation_id`` sắp theo **chờ lâu nhất trước** để kéo hàng
    đợi công bằng. Chỉ implementation ở infrastructure mới biết inbox tồn tại.
    """

    async def waiting_conversations(
        self, department_id: UUID, limit: int = 50
    ) -> tuple[UUID, ...]: ...
