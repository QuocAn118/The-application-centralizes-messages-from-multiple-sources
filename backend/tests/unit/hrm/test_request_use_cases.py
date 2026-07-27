from datetime import UTC, date, datetime

import pytest

from src.modules.hrm.application.actor import ActorRole, HrmActor
from src.modules.hrm.application.use_cases.request_use_cases import (
    ApproveRequest,
    CancelRequest,
    GetRequest,
    ListRequests,
    RejectRequest,
    SubmitRequest,
)
from src.modules.hrm.domain.entities.leave_request import (
    MissingLeavePeriodError,
    RequestNotPendingError,
)
from src.modules.hrm.domain.ports import (
    CHANGE_REQUEST_DECIDED,
    CHANGE_REQUEST_SUBMITTED,
    AgentInfo,
)
from src.modules.hrm.domain.value_objects.request_kind import (
    RequestStatus,
    RequestType,
)
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.hrm.fakes import (
    FakeClock,
    FakeNotifier,
    FakeRequestRepository,
    FakeWorkforceDirectory,
)

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
PHONG_A = new_id()
PHONG_B = new_id()


class _Boi:
    def __init__(self) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.repo = FakeRequestRepository()
        self.directory = FakeWorkforceDirectory()
        self.notifier = FakeNotifier()
        self.submit = SubmitRequest(self.repo, self.directory, self.notifier, self.clock)
        self.cancel = CancelRequest(self.repo, self.clock)
        self.approve = ApproveRequest(self.repo, self.directory, self.notifier, self.clock)
        self.reject = RejectRequest(self.repo, self.directory, self.notifier, self.clock)
        self.list = ListRequests(self.repo)
        self.get = GetRequest(self.repo)

    def them(self, role: str, department_id=PHONG_A):
        uid = new_id()
        self.directory.add_agent(
            AgentInfo(user_id=uid, department_id=department_id, role=role, is_active=True)
        )
        return uid

    def actor(self, uid, role: ActorRole, department_id=PHONG_A) -> HrmActor:
        return HrmActor(user_id=uid, role=role, department_id=department_id)


class TestSubmitRequest:
    async def test_staff_gui_don_nghi_phep(self) -> None:
        bc = _Boi()
        manager = bc.them("MANAGER", PHONG_A)
        staff = bc.them("STAFF", PHONG_A)

        view = await bc.submit.execute(
            bc.actor(staff, ActorRole.STAFF),
            RequestType.NGHI_PHEP,
            "Việc nhà",
            leave_start=date(2026, 8, 10),
            leave_end=date(2026, 8, 12),
        )

        assert view.status is RequestStatus.CHO_DUYET
        assert view.department_id == PHONG_A
        # Manager phòng đó được báo có đơn mới.
        assert bc.notifier.signals == [(view.id, manager, CHANGE_REQUEST_SUBMITTED)]

    async def test_gui_don_tang_luong_khong_can_khoang_thoi_gian(self) -> None:
        bc = _Boi()
        bc.them("MANAGER", PHONG_A)
        staff = bc.them("STAFF", PHONG_A)

        view = await bc.submit.execute(
            bc.actor(staff, ActorRole.STAFF), RequestType.TANG_LUONG, "Xin tăng lương"
        )

        assert view.status is RequestStatus.CHO_DUYET

    async def test_nghi_phep_thieu_khoang_thoi_gian_bi_tu_choi(self) -> None:
        bc = _Boi()
        staff = bc.them("STAFF", PHONG_A)

        with pytest.raises(MissingLeavePeriodError):
            await bc.submit.execute(bc.actor(staff, ActorRole.STAFF), RequestType.NGHI_PHEP, "Nghỉ")

    async def test_nguoi_khong_thuoc_phong_khong_gui_duoc(self) -> None:
        bc = _Boi()
        # Actor không có trong danh bạ -> get_agent trả None.
        with pytest.raises(PermissionDeniedError):
            await bc.submit.execute(bc.actor(new_id(), ActorRole.STAFF), RequestType.KHAC, "x")


class TestCancelRequest:
    async def test_chu_don_thu_hoi(self) -> None:
        bc = _Boi()
        bc.them("MANAGER", PHONG_A)
        staff = bc.them("STAFF", PHONG_A)
        don = await bc.submit.execute(bc.actor(staff, ActorRole.STAFF), RequestType.TANG_LUONG, "x")

        view = await bc.cancel.execute(bc.actor(staff, ActorRole.STAFF), don.id)

        assert view.status is RequestStatus.DA_HUY

    async def test_nguoi_khac_khong_thu_hoi_duoc(self) -> None:
        bc = _Boi()
        bc.them("MANAGER", PHONG_A)
        staff = bc.them("STAFF", PHONG_A)
        don = await bc.submit.execute(bc.actor(staff, ActorRole.STAFF), RequestType.TANG_LUONG, "x")
        nguoi_khac = bc.them("STAFF", PHONG_A)

        with pytest.raises(PermissionDeniedError):
            await bc.cancel.execute(bc.actor(nguoi_khac, ActorRole.STAFF), don.id)

    async def test_thu_hoi_don_da_duyet_bi_tu_choi(self) -> None:
        bc = _Boi()
        manager = bc.them("MANAGER", PHONG_A)
        staff = bc.them("STAFF", PHONG_A)
        don = await bc.submit.execute(bc.actor(staff, ActorRole.STAFF), RequestType.TANG_LUONG, "x")
        await bc.approve.execute(bc.actor(manager, ActorRole.MANAGER), don.id)

        with pytest.raises(RequestNotPendingError):
            await bc.cancel.execute(bc.actor(staff, ActorRole.STAFF), don.id)


class TestApproveReject:
    async def test_manager_duyet_don_staff_phong_minh(self) -> None:
        bc = _Boi()
        manager = bc.them("MANAGER", PHONG_A)
        staff = bc.them("STAFF", PHONG_A)
        don = await bc.submit.execute(bc.actor(staff, ActorRole.STAFF), RequestType.TANG_LUONG, "x")
        bc.notifier.signals.clear()

        view = await bc.approve.execute(bc.actor(manager, ActorRole.MANAGER), don.id)

        assert view.status is RequestStatus.DA_DUYET
        assert view.decided_by == manager
        # Người gửi được báo có quyết định.
        assert bc.notifier.signals == [(don.id, staff, CHANGE_REQUEST_DECIDED)]

    async def test_manager_tu_choi_kem_ly_do(self) -> None:
        bc = _Boi()
        manager = bc.them("MANAGER", PHONG_A)
        staff = bc.them("STAFF", PHONG_A)
        don = await bc.submit.execute(bc.actor(staff, ActorRole.STAFF), RequestType.TANG_LUONG, "x")

        view = await bc.reject.execute(
            bc.actor(manager, ActorRole.MANAGER), don.id, "Chưa đủ điều kiện"
        )

        assert view.status is RequestStatus.TU_CHOI
        assert view.decision_reason == "Chưa đủ điều kiện"

    async def test_manager_khong_duyet_don_phong_khac(self) -> None:
        bc = _Boi()
        bc.them("MANAGER", PHONG_A)
        staff_b = bc.them("STAFF", PHONG_B)
        manager_a = bc.them("MANAGER", PHONG_A)
        don = await bc.submit.execute(
            bc.actor(staff_b, ActorRole.STAFF, PHONG_B), RequestType.TANG_LUONG, "x"
        )

        with pytest.raises(PermissionDeniedError):
            await bc.approve.execute(bc.actor(manager_a, ActorRole.MANAGER, PHONG_A), don.id)

    async def test_manager_khong_tu_duyet_don_cua_minh(self) -> None:
        bc = _Boi()
        manager = bc.them("MANAGER", PHONG_A)
        don = await bc.submit.execute(
            bc.actor(manager, ActorRole.MANAGER), RequestType.TANG_LUONG, "x"
        )

        with pytest.raises(PermissionDeniedError):
            await bc.approve.execute(bc.actor(manager, ActorRole.MANAGER), don.id)

    async def test_don_cua_manager_do_admin_duyet(self) -> None:
        bc = _Boi()
        manager = bc.them("MANAGER", PHONG_A)
        don = await bc.submit.execute(
            bc.actor(manager, ActorRole.MANAGER), RequestType.TANG_LUONG, "x"
        )
        admin = new_id()

        view = await bc.approve.execute(bc.actor(admin, ActorRole.ADMIN, None), don.id)

        assert view.status is RequestStatus.DA_DUYET

    async def test_tu_choi_khong_ly_do_bi_chan(self) -> None:
        bc = _Boi()
        manager = bc.them("MANAGER", PHONG_A)
        staff = bc.them("STAFF", PHONG_A)
        don = await bc.submit.execute(bc.actor(staff, ActorRole.STAFF), RequestType.TANG_LUONG, "x")

        from src.modules.hrm.domain.entities.leave_request import (
            MissingRejectionReasonError,
        )

        with pytest.raises(MissingRejectionReasonError):
            await bc.reject.execute(bc.actor(manager, ActorRole.MANAGER), don.id, "  ")

    async def test_khong_duyet_lai_don_da_quyet(self) -> None:
        bc = _Boi()
        manager = bc.them("MANAGER", PHONG_A)
        staff = bc.them("STAFF", PHONG_A)
        don = await bc.submit.execute(bc.actor(staff, ActorRole.STAFF), RequestType.TANG_LUONG, "x")
        await bc.approve.execute(bc.actor(manager, ActorRole.MANAGER), don.id)

        with pytest.raises(RequestNotPendingError):
            await bc.approve.execute(bc.actor(manager, ActorRole.MANAGER), don.id)


class TestListGetRequests:
    async def test_staff_chi_thay_don_cua_minh(self) -> None:
        bc = _Boi()
        bc.them("MANAGER", PHONG_A)
        staff = bc.them("STAFF", PHONG_A)
        nguoi_khac = bc.them("STAFF", PHONG_A)
        await bc.submit.execute(bc.actor(staff, ActorRole.STAFF), RequestType.KHAC, "cua toi")
        await bc.submit.execute(
            bc.actor(nguoi_khac, ActorRole.STAFF), RequestType.KHAC, "cua nguoi khac"
        )

        page = await bc.list.execute(bc.actor(staff, ActorRole.STAFF))

        assert page.total == 1
        assert page.items[0].requester_id == staff

    async def test_manager_thay_don_ca_phong(self) -> None:
        bc = _Boi()
        manager = bc.them("MANAGER", PHONG_A)
        staff = bc.them("STAFF", PHONG_A)
        await bc.submit.execute(bc.actor(staff, ActorRole.STAFF), RequestType.KHAC, "x")
        await bc.submit.execute(bc.actor(manager, ActorRole.MANAGER), RequestType.KHAC, "y")

        page = await bc.list.execute(bc.actor(manager, ActorRole.MANAGER))

        assert page.total == 2

    async def test_get_don_nguoi_khac_bi_tu_choi(self) -> None:
        bc = _Boi()
        bc.them("MANAGER", PHONG_A)
        staff = bc.them("STAFF", PHONG_A)
        nguoi_khac = bc.them("STAFF", PHONG_A)
        don = await bc.submit.execute(bc.actor(nguoi_khac, ActorRole.STAFF), RequestType.KHAC, "x")

        with pytest.raises(PermissionDeniedError):
            await bc.get.execute(bc.actor(staff, ActorRole.STAFF), don.id)

    async def test_get_don_khong_ton_tai(self) -> None:
        bc = _Boi()
        staff = bc.them("STAFF", PHONG_A)

        with pytest.raises(NotFoundError):
            await bc.get.execute(bc.actor(staff, ActorRole.STAFF), new_id())
