"""Test use case AutoAssignConversation với fake."""

from uuid import UUID

from src.modules.assignment.application.use_cases.auto_assign_conversation import (
    AutoAssignConversation,
)
from src.modules.assignment.domain.ports import AssignResult
from src.modules.assignment.domain.value_objects.candidate import (
    AgentCandidate,
    AssignmentOutcome,
)
from tests.unit.assignment.fakes import FakeAgentPool, FakeConversationAssigner

PHONG = UUID("00000000-0000-0000-0000-0000000000d1")
CONV = UUID("00000000-0000-0000-0000-0000000000c1")
A = UUID("00000000-0000-0000-0000-0000000000a1")
B = UUID("00000000-0000-0000-0000-0000000000b2")


class TestAutoAssign:
    async def test_gan_nguoi_trong_ca_tai_thap(self) -> None:
        pool = FakeAgentPool(
            {
                PHONG: (
                    AgentCandidate(user_id=A, on_shift=True, open_load=3),
                    AgentCandidate(user_id=B, on_shift=True, open_load=1),
                )
            }
        )
        assigner = FakeConversationAssigner(succeed=True)

        outcome = await AutoAssignConversation(pool, assigner).execute(CONV, PHONG)

        assert outcome is AssignmentOutcome.ASSIGNED
        assert assigner.assigned == [(CONV, B, PHONG)]

    async def test_khong_ai_trong_ca_thi_queued(self) -> None:
        pool = FakeAgentPool({PHONG: (AgentCandidate(user_id=A, on_shift=False, open_load=0),)})
        assigner = FakeConversationAssigner(succeed=True)

        outcome = await AutoAssignConversation(pool, assigner).execute(CONV, PHONG)

        assert outcome is AssignmentOutcome.QUEUED
        assert assigner.assigned == []

    async def test_phong_rong_thi_queued(self) -> None:
        outcome = await AutoAssignConversation(
            FakeAgentPool({}), FakeConversationAssigner()
        ).execute(CONV, PHONG)
        assert outcome is AssignmentOutcome.QUEUED

    async def test_gan_bi_tu_choi_thi_queued_khong_nem(self) -> None:
        # #1 từ chối (REJECTED: không còn DANG_MO…) -> QUEUED, không lỗi.
        pool = FakeAgentPool({PHONG: (AgentCandidate(user_id=A, on_shift=True, open_load=0),)})
        assigner = FakeConversationAssigner(succeed=False)

        outcome = await AutoAssignConversation(pool, assigner).execute(CONV, PHONG)

        assert outcome is AssignmentOutcome.QUEUED
        assert assigner.assigned == [(CONV, A, PHONG)]  # có thử gán

    async def test_vua_co_nguoi_nhan_thi_skipped(self) -> None:
        # ALREADY_TAKEN (race: hội thoại vừa có người khác nhận) -> SKIPPED, KHÔNG
        # phải QUEUED — hội thoại đã có chủ, không còn trong hàng đợi.
        pool = FakeAgentPool({PHONG: (AgentCandidate(user_id=A, on_shift=True, open_load=0),)})
        assigner = FakeConversationAssigner(result=AssignResult.ALREADY_TAKEN)

        outcome = await AutoAssignConversation(pool, assigner).execute(CONV, PHONG)

        assert outcome is AssignmentOutcome.SKIPPED
