"""Fake cho các port của assignment — tất định, dùng trong test use case."""

from uuid import UUID

from src.modules.assignment.domain.ports import AssignResult
from src.modules.assignment.domain.value_objects.candidate import AgentCandidate


class FakeAgentPool:
    """``IAgentPool`` giả: trả sẵn ứng viên theo phòng."""

    def __init__(self, by_department: dict[UUID, tuple[AgentCandidate, ...]] | None = None) -> None:
        self._by_department = by_department or {}
        self.calls: list[UUID] = []

    async def candidates_for_department(self, department_id: UUID) -> tuple[AgentCandidate, ...]:
        self.calls.append(department_id)
        return self._by_department.get(department_id, ())


class FakeConversationAssigner:
    """``IConversationAssigner`` giả: ghi lại lời gán, cấu hình kết quả.

    ``succeed`` là lối tắt: True→ASSIGNED, False→REJECTED. Truyền ``result`` để
    kiểm nhánh ALREADY_TAKEN.
    """

    def __init__(self, succeed: bool = True, result: AssignResult | None = None) -> None:
        self._result = result or (AssignResult.ASSIGNED if succeed else AssignResult.REJECTED)
        self.assigned: list[tuple[UUID, UUID]] = []

    async def assign_to_agent(self, conversation_id: UUID, user_id: UUID) -> AssignResult:
        self.assigned.append((conversation_id, user_id))
        return self._result


class FakeWaitingQueue:
    """``IWaitingQueue`` giả: trả sẵn hàng đợi theo phòng."""

    def __init__(self, by_department: dict[UUID, tuple[UUID, ...]] | None = None) -> None:
        self._by_department = by_department or {}
        self.calls: list[UUID] = []

    async def waiting_conversations(self, department_id: UUID, limit: int = 50) -> tuple[UUID, ...]:
        self.calls.append(department_id)
        return self._by_department.get(department_id, ())[:limit]
