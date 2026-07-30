"""Use case: kéo hàng đợi một phòng, gán các hội thoại chờ cho người rảnh.

Trigger: khi một nhân viên vừa đóng một hội thoại (rảnh ra), hoặc Manager kích
hoạt thủ công. Lấy hàng đợi phòng (hội thoại ``DANG_MO`` chưa gán, chờ lâu nhất
trước) và danh sách ứng viên; gán lần lượt tới khi hết việc hoặc hết người trong
ca. Sau mỗi lần gán thành công, **tăng tải trong bộ nhớ** của người vừa nhận để
lượt kế cân bằng sang người khác (không truy vấn lại pool mỗi hội thoại).

Không ném lỗi khi một lần gán bị khước từ (race) — bỏ qua hội thoại đó, thử tiếp.
"""

import logging
from dataclasses import replace
from uuid import UUID

from src.modules.assignment.domain.ports import (
    IAgentPool,
    IConversationAssigner,
    IWaitingQueue,
)
from src.modules.assignment.domain.services.selector import chon_nhan_vien
from src.modules.assignment.domain.value_objects.candidate import AgentCandidate

logger = logging.getLogger(__name__)


class PullDepartmentQueue:
    """Kéo hàng đợi phòng, gán cho các nhân viên đang trong ca."""

    def __init__(
        self,
        agent_pool: IAgentPool,
        waiting_queue: IWaitingQueue,
        assigner: IConversationAssigner,
    ) -> None:
        self._agent_pool = agent_pool
        self._waiting_queue = waiting_queue
        self._assigner = assigner

    async def execute(self, department_id: UUID, limit: int = 50) -> int:
        """Gán tối đa các hội thoại chờ; trả số hội thoại đã gán được."""
        waiting = await self._waiting_queue.waiting_conversations(department_id, limit)
        if not waiting:
            return 0

        # Bản sao tải để mô phỏng cân bằng trong một lượt kéo, không đụng pool.
        candidates: dict[UUID, AgentCandidate] = {
            c.user_id: c for c in await self._agent_pool.candidates_for_department(department_id)
        }

        da_gan = 0
        for conversation_id in waiting:
            chon = chon_nhan_vien(tuple(candidates.values()))
            if chon is None:
                # Không còn ai trong ca → phần còn lại của hàng đợi vẫn chờ.
                break
            if await self._assigner.assign_to_agent(conversation_id, chon):
                da_gan += 1
                # Tăng tải người vừa nhận để lượt kế ưu tiên người khác.
                cu = candidates[chon]
                candidates[chon] = replace(cu, open_load=cu.open_load + 1)
            else:
                logger.info(
                    "Kéo hàng đợi: gán bị khước từ, bỏ qua",
                    extra={
                        "conversation_id": str(conversation_id),
                        "user_id": str(chon),
                    },
                )
        return da_gan
