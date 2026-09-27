"""BE-2: Manager/Admin giao, đổi, gỡ người phụ trách (redesign Phần 2a).

Quy tắc đã duyệt: chỉ Manager (hội thoại thuộc phòng mình) hoặc Admin; người được
giao đang hoạt động và CÙNG PHÒNG với hội thoại; hội thoại phải DANG_MO. Mỗi lần
đổi ghi một sự kiện timeline và báo riêng người được giao / người bị gỡ.
"""

from datetime import UTC, datetime

import pytest

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.change_assignee import ChangeAssignee
from src.modules.inbox.domain.entities.conversation import (
    AlreadyAssignedToUserError,
    Conversation,
    NotAssignedError,
)
from src.modules.inbox.domain.entities.conversation_event import ConversationEventKind
from src.modules.inbox.domain.ports import (
    CHANGE_ASSIGNED_TO_YOU,
    CHANGE_UNASSIGNED_FROM_YOU,
    AgentInfo,
)
from src.shared.application.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from src.shared.domain.identifiers import new_id
from tests.unit.inbox.fakes import (
    FakeClock,
    FakeConversationEventRepository,
    FakeConversationRepository,
    FakeRealtimeNotifier,
    FakeWorkforceDirectory,
)

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)
PHONG_A, PHONG_B = new_id(), new_id()
A, B = new_id(), new_id()
ADMIN = InboxActor(user_id=new_id(), role=ActorRole.ADMIN)
MANAGER_A = InboxActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=PHONG_A)


def _nv(user_id, department_id=PHONG_A, is_active=True) -> AgentInfo:
    return AgentInfo(
        user_id=user_id,
        department_id=department_id,
        role="STAFF",
        is_active=is_active,
        full_name=f"NV {str(user_id)[:4]}",
    )


class _BoiCanh:
    def __init__(self, department_id=PHONG_A, nguoi_hien_tai=None) -> None:
        self.ht = Conversation.start(
            channel_id=new_id(), customer_id=new_id(), department_id=department_id, now=BAY_GIO
        )
        if nguoi_hien_tai is not None:
            self.ht.assign_to_agent(nguoi_hien_tai, BAY_GIO)
        self.repo = FakeConversationRepository()
        self.repo._conversations[self.ht.id] = self.ht
        self.events = FakeConversationEventRepository()
        self.notifier = FakeRealtimeNotifier()
        self.directory = FakeWorkforceDirectory(
            [_nv(A), _nv(B), _nv(new_id(), PHONG_B), _nv(n := new_id(), is_active=False)]
        )
        self.nghi_viec = n
        self.uc = ChangeAssignee(
            self.repo, self.events, self.directory, self.notifier, FakeClock(BAY_GIO)
        )


class TestGiaoDoiGo:
    async def test_giao_khi_chua_co_ai(self) -> None:
        bc = _BoiCanh()

        _, su_kien = await bc.uc.execute(MANAGER_A, bc.ht.id, A)

        assert bc.ht.assigned_user_id == A
        assert su_kien.kind is ConversationEventKind.ASSIGNED
        assert (su_kien.actor_user_id, su_kien.from_user_id, su_kien.to_user_id) == (
            MANAGER_A.user_id,
            None,
            A,
        )
        assert bc.events.events == [su_kien]

    async def test_doi_nguoi(self) -> None:
        bc = _BoiCanh(nguoi_hien_tai=A)

        _, su_kien = await bc.uc.execute(ADMIN, bc.ht.id, B)

        assert bc.ht.assigned_user_id == B
        assert su_kien.kind is ConversationEventKind.REASSIGNED
        assert (su_kien.from_user_id, su_kien.to_user_id) == (A, B)

    async def test_go_nguoi(self) -> None:
        bc = _BoiCanh(nguoi_hien_tai=A)

        _, su_kien = await bc.uc.execute(MANAGER_A, bc.ht.id, None)

        assert bc.ht.assigned_user_id is None
        assert su_kien.kind is ConversationEventKind.UNASSIGNED
        assert (su_kien.from_user_id, su_kien.to_user_id) == (A, None)


class TestTinHieuRieng:
    """Quyết định #5: phát sự kiện cho người được giao VÀ người bị gỡ."""

    async def test_doi_nguoi_bao_ca_hai(self) -> None:
        bc = _BoiCanh(nguoi_hien_tai=A)

        await bc.uc.execute(ADMIN, bc.ht.id, B)

        assert set(bc.notifier.rieng) == {
            (B, bc.ht.id, CHANGE_ASSIGNED_TO_YOU),
            (A, bc.ht.id, CHANGE_UNASSIGNED_FROM_YOU),
        }
        assert len(bc.notifier.signals) == 1  # tín hiệu chung cho phòng vẫn có

    async def test_go_chi_bao_nguoi_bi_go(self) -> None:
        bc = _BoiCanh(nguoi_hien_tai=A)

        await bc.uc.execute(ADMIN, bc.ht.id, None)

        assert bc.notifier.rieng == [(A, bc.ht.id, CHANGE_UNASSIGNED_FROM_YOU)]


class TestQuyen:
    async def test_staff_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        staff = InboxActor(user_id=A, role=ActorRole.STAFF, department_id=PHONG_A)

        with pytest.raises(PermissionDeniedError):
            await bc.uc.execute(staff, bc.ht.id, A)
        assert bc.events.events == []

    async def test_manager_phong_khac_bi_tu_choi(self) -> None:
        bc = _BoiCanh(department_id=PHONG_B)

        with pytest.raises(PermissionDeniedError):
            await bc.uc.execute(MANAGER_A, bc.ht.id, A)

    async def test_giao_cho_nguoi_phong_khac_bi_tu_choi(self) -> None:
        bc = _BoiCanh()
        nguoi_phong_b = next(
            u for u, a in bc.directory._agents.items() if a.department_id == PHONG_B
        )

        with pytest.raises(PermissionDeniedError):
            await bc.uc.execute(ADMIN, bc.ht.id, nguoi_phong_b)
        assert bc.ht.assigned_user_id is None

    async def test_giao_cho_nguoi_da_nghi_bi_tu_choi(self) -> None:
        bc = _BoiCanh()

        with pytest.raises(NotFoundError):
            await bc.uc.execute(ADMIN, bc.ht.id, bc.nghi_viec)

    async def test_hoi_thoai_khong_ton_tai(self) -> None:
        bc = _BoiCanh()
        with pytest.raises(NotFoundError):
            await bc.uc.execute(ADMIN, new_id(), A)


class TestBatBien:
    async def test_doi_sang_chinh_nguoi_do(self) -> None:
        bc = _BoiCanh(nguoi_hien_tai=A)
        with pytest.raises(AlreadyAssignedToUserError):
            await bc.uc.execute(ADMIN, bc.ht.id, A)

    async def test_go_khi_chua_co_ai(self) -> None:
        bc = _BoiCanh()
        with pytest.raises(NotAssignedError):
            await bc.uc.execute(ADMIN, bc.ht.id, None)

    async def test_xung_dot_khong_ghi_su_kien_khong_bao(self) -> None:
        """Review Focus #1: đã có người đổi trước → 409, không để timeline lệch."""
        bc = _BoiCanh(nguoi_hien_tai=A)
        bc.repo.ep_xung_dot = True

        with pytest.raises(ConflictError):
            await bc.uc.execute(ADMIN, bc.ht.id, B)
        assert bc.events.events == []
        assert bc.notifier.rieng == []
