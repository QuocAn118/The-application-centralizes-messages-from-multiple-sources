"""Test use case AssignConversationToAgent (#1) — giao việc cho nhân viên khác.

Khác TakeConversation (tự nhận): Manager/Admin/hệ thống giao cho một người cụ
thể. Kiểm phạm vi phòng, nhân viên phải active + đúng phòng, và máy trạng thái
(chỉ DANG_MO chưa có người).
"""

from datetime import UTC, datetime

import pytest

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.assign_conversation_to_agent import (
    AssignConversationToAgent,
)
from src.modules.inbox.domain.entities.conversation import (
    AlreadyAssignedError,
    Conversation,
    NotOpenError,
)
from src.modules.inbox.domain.ports import AgentInfo
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.inbox.fakes import (
    FakeClock,
    FakeConversationRepository,
    FakeRealtimeNotifier,
    FakeWorkforceDirectory,
)

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)
PHONG = new_id()
NHAN_VIEN = new_id()


def _dang_mo(department_id=PHONG) -> Conversation:
    return Conversation.start(
        channel_id=new_id(), customer_id=new_id(), department_id=department_id, now=BAY_GIO
    )


def _agent(user_id=NHAN_VIEN, department_id=PHONG, is_active=True) -> AgentInfo:
    return AgentInfo(
        user_id=user_id, department_id=department_id, role="STAFF", is_active=is_active
    )


async def _dung(conversation: Conversation, agents: list[AgentInfo]):
    repo = FakeConversationRepository()
    await repo.add(conversation)
    directory = FakeWorkforceDirectory(agents)
    notifier = FakeRealtimeNotifier()
    uc = AssignConversationToAgent(repo, directory, notifier, FakeClock(BAY_GIO))
    return uc, repo, notifier


ADMIN = InboxActor(user_id=new_id(), role=ActorRole.ADMIN)
MANAGER = InboxActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=PHONG)


class TestAssignAgent:
    async def test_admin_giao_viec_thanh_cong(self) -> None:
        ht = _dang_mo()
        uc, repo, notifier = await _dung(ht, [_agent()])

        await uc.execute(ADMIN, ht.id, NHAN_VIEN)

        moi = await repo.get_by_id(ht.id)
        assert moi is not None
        assert moi.assigned_user_id == NHAN_VIEN
        assert len(notifier.signals) == 1

    async def test_staff_bi_tu_choi(self) -> None:
        ht = _dang_mo()
        uc, _, _ = await _dung(ht, [_agent()])
        staff = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG)
        with pytest.raises(PermissionDeniedError):
            await uc.execute(staff, ht.id, NHAN_VIEN)

    async def test_manager_khong_giao_viec_phong_khac(self) -> None:
        ht = _dang_mo(department_id=new_id())  # hội thoại phòng khác
        uc, _, _ = await _dung(ht, [_agent()])
        with pytest.raises(PermissionDeniedError):
            await uc.execute(MANAGER, ht.id, NHAN_VIEN)

    async def test_nhan_vien_khac_phong_bi_chan(self) -> None:
        ht = _dang_mo()
        # Nhân viên thuộc phòng khác với hội thoại.
        uc, _, _ = await _dung(ht, [_agent(department_id=new_id())])
        with pytest.raises(PermissionDeniedError):
            await uc.execute(ADMIN, ht.id, NHAN_VIEN)

    async def test_nhan_vien_khong_active_bi_chan(self) -> None:
        ht = _dang_mo()
        uc, _, _ = await _dung(ht, [_agent(is_active=False)])
        with pytest.raises(NotFoundError):
            await uc.execute(ADMIN, ht.id, NHAN_VIEN)

    async def test_nhan_vien_khong_ton_tai(self) -> None:
        ht = _dang_mo()
        uc, _, _ = await _dung(ht, [])
        with pytest.raises(NotFoundError):
            await uc.execute(ADMIN, ht.id, NHAN_VIEN)

    async def test_hoi_thoai_khong_ton_tai(self) -> None:
        uc, _, _ = await _dung(_dang_mo(), [_agent()])
        with pytest.raises(NotFoundError):
            await uc.execute(ADMIN, new_id(), NHAN_VIEN)

    async def test_da_co_nguoi_thi_chan(self) -> None:
        ht = _dang_mo()
        ht.assign_to_agent(new_id(), BAY_GIO)  # đã có người
        uc, _, _ = await _dung(ht, [_agent()])
        with pytest.raises(AlreadyAssignedError):
            await uc.execute(ADMIN, ht.id, NHAN_VIEN)

    async def test_hoi_thoai_cho_phan_chua_co_phong_thi_chan(self) -> None:
        # CHO_PHAN (department_id=None) chưa mở -> assign_to_agent ném NotOpenError.
        ht = Conversation.start(
            channel_id=new_id(), customer_id=new_id(), department_id=None, now=BAY_GIO
        )
        uc, _, _ = await _dung(ht, [_agent(department_id=None)])
        with pytest.raises(NotOpenError):
            await uc.execute(ADMIN, ht.id, NHAN_VIEN)
