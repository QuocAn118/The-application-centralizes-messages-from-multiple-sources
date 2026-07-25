from datetime import UTC, datetime

import pytest

from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.assign_conversation_to_department import (
    AssignConversationToDepartment,
)
from src.modules.inbox.application.use_cases.close_conversation import CloseConversation
from src.modules.inbox.application.use_cases.take_conversation import TakeConversation
from src.modules.inbox.domain.entities.conversation import (
    AlreadyAssignedError,
    Conversation,
    ConversationStatus,
    NotAwaitingAssignmentError,
)
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.inbox.fakes import (
    FakeClock,
    FakeConversationRepository,
    FakeRealtimeNotifier,
    FakeWorkforceDirectory,
)

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)
PHONG_A = new_id()


def _cho_phan() -> Conversation:
    return Conversation.start(
        channel_id=new_id(), customer_id=new_id(), department_id=None, now=BAY_GIO
    )


def _dang_mo(department_id=PHONG_A) -> Conversation:
    return Conversation.start(
        channel_id=new_id(), customer_id=new_id(), department_id=department_id, now=BAY_GIO
    )


class TestPhanPhong:
    async def _dung(self, conversation: Conversation):
        repo = FakeConversationRepository()
        await repo.add(conversation)
        directory = FakeWorkforceDirectory()
        directory.active_departments.add(PHONG_A)
        notifier = FakeRealtimeNotifier()
        uc = AssignConversationToDepartment(repo, directory, notifier, FakeClock(BAY_GIO))
        return uc, repo, notifier

    async def test_manager_phan_hoi_thoai_cho_phan(self) -> None:
        ht = _cho_phan()
        uc, repo, notifier = await self._dung(ht)
        manager = InboxActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=PHONG_A)

        await uc.execute(manager, ht.id, PHONG_A)

        moi = await repo.get_by_id(ht.id)
        assert moi is not None
        assert moi.status is ConversationStatus.DANG_MO
        assert moi.department_id == PHONG_A
        assert len(notifier.signals) == 1

    async def test_staff_khong_duoc_phan(self) -> None:
        ht = _cho_phan()
        uc, _, _ = await self._dung(ht)
        staff = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)

        with pytest.raises(PermissionDeniedError):
            await uc.execute(staff, ht.id, PHONG_A)

    async def test_manager_khong_phan_ra_ngoai_phong_minh(self) -> None:
        ht = _cho_phan()
        uc, _, _ = await self._dung(ht)
        manager = InboxActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=new_id())

        with pytest.raises(PermissionDeniedError):
            await uc.execute(manager, ht.id, PHONG_A)

    async def test_phong_khong_hoat_dong_bi_tu_choi(self) -> None:
        ht = _cho_phan()
        repo = FakeConversationRepository()
        await repo.add(ht)
        directory = FakeWorkforceDirectory()  # không có phòng nào active
        uc = AssignConversationToDepartment(
            repo, directory, FakeRealtimeNotifier(), FakeClock(BAY_GIO)
        )
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        with pytest.raises(NotFoundError):
            await uc.execute(admin, ht.id, PHONG_A)

    async def test_hoi_thoai_dang_mo_khong_phan_lai_duoc(self) -> None:
        ht = _dang_mo()
        uc, _, _ = await self._dung(ht)
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        with pytest.raises(NotAwaitingAssignmentError):
            await uc.execute(admin, ht.id, PHONG_A)

    async def test_hoi_thoai_khong_ton_tai(self) -> None:
        uc, _, _ = await self._dung(_cho_phan())
        admin = InboxActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)

        with pytest.raises(NotFoundError):
            await uc.execute(admin, new_id(), PHONG_A)


class TestNhanHoiThoai:
    async def _dung(self, conversation: Conversation):
        repo = FakeConversationRepository()
        await repo.add(conversation)
        notifier = FakeRealtimeNotifier()
        uc = TakeConversation(repo, notifier, FakeClock(BAY_GIO))
        return uc, repo, notifier

    async def test_nhan_vien_nhan_hoi_thoai_dang_mo(self) -> None:
        ht = _dang_mo()
        uc, repo, _ = await self._dung(ht)
        nv = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)

        await uc.execute(nv, ht.id)

        moi = await repo.get_by_id(ht.id)
        assert moi is not None
        assert moi.assigned_user_id == nv.user_id

    async def test_khong_nhan_hoi_thoai_da_co_nguoi(self) -> None:
        ht = _dang_mo()
        ht.assign_to_agent(new_id(), BAY_GIO)
        uc, _, _ = await self._dung(ht)
        nv = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)

        with pytest.raises(AlreadyAssignedError):
            await uc.execute(nv, ht.id)

    async def test_nhan_vien_khac_phong_bi_tu_choi(self) -> None:
        ht = _dang_mo(department_id=PHONG_A)
        uc, _, _ = await self._dung(ht)
        nguoi_la = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=new_id())

        with pytest.raises(PermissionDeniedError):
            await uc.execute(nguoi_la, ht.id)

    async def test_hoi_thoai_khong_ton_tai(self) -> None:
        uc, _, _ = await self._dung(_dang_mo())
        nv = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)

        with pytest.raises(NotFoundError):
            await uc.execute(nv, new_id())


class TestDongHoiThoai:
    async def _dung(self, conversation: Conversation):
        repo = FakeConversationRepository()
        await repo.add(conversation)
        notifier = FakeRealtimeNotifier()
        uc = CloseConversation(repo, notifier, FakeClock(BAY_GIO))
        return uc, repo, notifier

    async def test_dong_hoi_thoai_dang_mo(self) -> None:
        ht = _dang_mo()
        uc, repo, notifier = await self._dung(ht)
        nv = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)

        await uc.execute(nv, ht.id)

        moi = await repo.get_by_id(ht.id)
        assert moi is not None
        assert moi.status is ConversationStatus.DA_DONG
        assert len(notifier.signals) == 1

    async def test_hoi_thoai_khong_ton_tai(self) -> None:
        uc, _, _ = await self._dung(_dang_mo())
        nv = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)

        with pytest.raises(NotFoundError):
            await uc.execute(nv, new_id())

    async def test_dong_roi_khach_nhan_lai_thi_mo_lai(self) -> None:
        ht = _dang_mo()
        ht.assign_to_agent(new_id(), BAY_GIO)
        nguoi_xu_ly = ht.assigned_user_id
        uc, repo, _ = await self._dung(ht)
        nv = InboxActor(user_id=new_id(), role=ActorRole.STAFF, department_id=PHONG_A)
        await uc.execute(nv, ht.id)

        # Khách nhắn lại (domain xử lý, ở đây gọi trực tiếp để kiểm bất biến).
        moi = await repo.get_by_id(ht.id)
        assert moi is not None
        moi.register_incoming(BAY_GIO)

        assert moi.status is ConversationStatus.DANG_MO
        assert moi.assigned_user_id == nguoi_xu_ly
