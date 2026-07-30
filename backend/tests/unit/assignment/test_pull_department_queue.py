"""Test use case PullDepartmentQueue với fake."""

from uuid import UUID

from src.modules.assignment.application.use_cases.pull_department_queue import (
    PullDepartmentQueue,
)
from src.modules.assignment.domain.value_objects.candidate import AgentCandidate
from tests.unit.assignment.fakes import (
    FakeAgentPool,
    FakeConversationAssigner,
    FakeWaitingQueue,
)

PHONG = UUID("00000000-0000-0000-0000-0000000000d1")
C1 = UUID("00000000-0000-0000-0000-0000000000c1")
C2 = UUID("00000000-0000-0000-0000-0000000000c2")
C3 = UUID("00000000-0000-0000-0000-0000000000c3")
A = UUID("00000000-0000-0000-0000-0000000000a1")
B = UUID("00000000-0000-0000-0000-0000000000b2")


class TestPullQueue:
    async def test_hang_doi_rong_thi_khong_gan(self) -> None:
        da_gan = await PullDepartmentQueue(
            FakeAgentPool({PHONG: (AgentCandidate(user_id=A, on_shift=True, open_load=0),)}),
            FakeWaitingQueue({}),
            FakeConversationAssigner(),
        ).execute(PHONG)
        assert da_gan == 0

    async def test_can_bang_tai_qua_cac_lan_gan(self) -> None:
        # 3 hội thoại chờ, 2 người tải bằng nhau -> chia luân phiên nhờ tăng tải
        # trong bộ nhớ: A, B, rồi A (A về lại tải thấp nhất sau khi B nhận).
        pool = FakeAgentPool(
            {
                PHONG: (
                    AgentCandidate(user_id=A, on_shift=True, open_load=0),
                    AgentCandidate(user_id=B, on_shift=True, open_load=0),
                )
            }
        )
        queue = FakeWaitingQueue({PHONG: (C1, C2, C3)})
        assigner = FakeConversationAssigner(succeed=True)

        da_gan = await PullDepartmentQueue(pool, queue, assigner).execute(PHONG)

        assert da_gan == 3
        # Hội thoại theo thứ tự chờ; người luân phiên A/B/A.
        assert [conv for conv, _ in assigner.assigned] == [C1, C2, C3]
        nguoi = [u for _, u in assigner.assigned]
        assert nguoi == [A, B, A]

    async def test_dung_khi_het_nguoi_trong_ca(self) -> None:
        # 2 việc chờ nhưng không ai trong ca -> không gán được, không lỗi.
        pool = FakeAgentPool({PHONG: (AgentCandidate(user_id=A, on_shift=False, open_load=0),)})
        queue = FakeWaitingQueue({PHONG: (C1, C2)})

        da_gan = await PullDepartmentQueue(pool, queue, FakeConversationAssigner()).execute(PHONG)

        assert da_gan == 0

    async def test_gan_khuoc_tu_thi_bo_qua_van_dem_dung(self) -> None:
        pool = FakeAgentPool({PHONG: (AgentCandidate(user_id=A, on_shift=True, open_load=0),)})
        queue = FakeWaitingQueue({PHONG: (C1, C2)})
        assigner = FakeConversationAssigner(succeed=False)  # mọi lần gán đều bị khước từ

        da_gan = await PullDepartmentQueue(pool, queue, assigner).execute(PHONG)

        assert da_gan == 0
        assert len(assigner.assigned) == 2  # đã thử cả hai
