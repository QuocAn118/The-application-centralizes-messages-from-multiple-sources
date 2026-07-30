"""Use case: tự chọn nhân viên và gán một hội thoại đã thuộc một phòng.

Trigger: ngay sau khi hội thoại được phân về phòng (#2 tự phân / Manager phân
tay). Lấy ứng viên của phòng (đang trong ca, tải, KPI, mốc gán) → bộ chọn xếp
theo chuỗi tiêu chí → gán qua ``IConversationAssigner`` (gọi use case của #1 với
actor hệ thống). Không ai trong ca / gán thất bại (race đã có người) → để hội
thoại trong hàng đợi phòng, KHÔNG ném lỗi (RB-4: auto-assign hỏng không làm hỏng
luồng gọi).
"""

import logging
from uuid import UUID

from src.modules.assignment.domain.ports import (
    AssignResult,
    IAgentPool,
    IConversationAssigner,
)
from src.modules.assignment.domain.services.selector import chon_nhan_vien
from src.modules.assignment.domain.value_objects.candidate import AssignmentOutcome

logger = logging.getLogger(__name__)


class AutoAssignConversation:
    """Chọn nhân viên và gán một hội thoại thuộc một phòng."""

    def __init__(self, agent_pool: IAgentPool, assigner: IConversationAssigner) -> None:
        self._agent_pool = agent_pool
        self._assigner = assigner

    async def execute(self, conversation_id: UUID, department_id: UUID) -> AssignmentOutcome:
        """Trả kết cục. ``ASSIGNED`` khi gán được; ``QUEUED`` khi không ai/khước từ."""
        candidates = await self._agent_pool.candidates_for_department(department_id)
        chon = chon_nhan_vien(candidates)
        if chon is None:
            # Không ai trong ca → hội thoại nằm trong hàng đợi phòng, chờ.
            return AssignmentOutcome.QUEUED

        ket_qua = await self._assigner.assign_to_agent(conversation_id, chon)
        if ket_qua is AssignResult.ASSIGNED:
            return AssignmentOutcome.ASSIGNED
        if ket_qua is AssignResult.ALREADY_TAKEN:
            # Hội thoại vừa có người khác nhận (race) — đã ổn, không phải hàng đợi.
            return AssignmentOutcome.SKIPPED

        # #1 từ chối vì lý do khác (không còn DANG_MO…) — để hàng đợi, lần kéo sau.
        logger.info(
            "Tự gán bị khước từ — để hàng đợi",
            extra={"conversation_id": str(conversation_id), "user_id": str(chon)},
        )
        return AssignmentOutcome.QUEUED
