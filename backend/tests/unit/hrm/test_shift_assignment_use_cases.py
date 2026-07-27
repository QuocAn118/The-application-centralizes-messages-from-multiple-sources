from datetime import UTC, date, datetime, time

import pytest

from src.modules.hrm.application.actor import ActorRole, HrmActor
from src.modules.hrm.application.use_cases.shift_assignment_use_cases import (
    AssignShift,
    CancelShiftAssignment,
    ListShiftAssignments,
    ShiftOverlapError,
)
from src.modules.hrm.domain.entities.shift import Shift
from src.modules.hrm.domain.entities.shift_assignment import (
    PastShiftDateError,
)
from src.modules.hrm.domain.ports import AgentInfo
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.hrm.fakes import (
    FakeClock,
    FakeShiftAssignmentRepository,
    FakeShiftRepository,
    FakeWorkforceDirectory,
)

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
PHONG_A = new_id()
PHONG_B = new_id()
NGAY = date(2026, 8, 5)


def _manager(department_id=PHONG_A) -> HrmActor:
    return HrmActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=department_id)


def _admin() -> HrmActor:
    return HrmActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)


def _staff(user_id, department_id=PHONG_A) -> HrmActor:
    return HrmActor(user_id=user_id, role=ActorRole.STAFF, department_id=department_id)


class _Boi:
    def __init__(self) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.assign_repo = FakeShiftAssignmentRepository()
        self.shift_repo = FakeShiftRepository()
        self.directory = FakeWorkforceDirectory()
        self.directory.active_departments = {PHONG_A, PHONG_B}
        self.assign = AssignShift(self.assign_repo, self.shift_repo, self.directory, self.clock)
        self.cancel = CancelShiftAssignment(self.assign_repo, self.clock)
        self.list = ListShiftAssignments(self.assign_repo)

    async def them_ca(self, department_id=PHONG_A, start=time(8, 0), end=time(12, 0)) -> Shift:
        ca = Shift.create(
            department_id=department_id, name="Ca", start_time=start, end_time=end, now=BAY_GIO
        )
        await self.shift_repo.add(ca)
        return ca

    def them_nhan_vien(self, department_id=PHONG_A):
        nv = new_id()
        self.directory.add_agent(
            AgentInfo(user_id=nv, department_id=department_id, role="STAFF", is_active=True)
        )
        return nv


class TestAssignShift:
    async def test_phan_ca_hop_le(self) -> None:
        bc = _Boi()
        ca = await bc.them_ca()
        nv = bc.them_nhan_vien(PHONG_A)

        view = await bc.assign.execute(_manager(), ca.id, nv, NGAY)

        assert view.user_id == nv
        assert view.work_date == NGAY
        assert view.start_time == time(8, 0)

    async def test_chong_ca_bi_tu_choi(self) -> None:
        bc = _Boi()
        ca1 = await bc.them_ca(start=time(8, 0), end=time(12, 0))
        ca2 = await bc.them_ca(start=time(11, 0), end=time(15, 0))
        nv = bc.them_nhan_vien(PHONG_A)
        await bc.assign.execute(_manager(), ca1.id, nv, NGAY)

        with pytest.raises(ShiftOverlapError):
            await bc.assign.execute(_manager(), ca2.id, nv, NGAY)

    async def test_ca_ke_nhau_khong_bi_coi_la_chong(self) -> None:
        bc = _Boi()
        ca1 = await bc.them_ca(start=time(8, 0), end=time(12, 0))
        ca2 = await bc.them_ca(start=time(12, 0), end=time(16, 0))
        nv = bc.them_nhan_vien(PHONG_A)
        await bc.assign.execute(_manager(), ca1.id, nv, NGAY)

        view = await bc.assign.execute(_manager(), ca2.id, nv, NGAY)

        assert view.start_time == time(12, 0)

    async def test_ngay_qua_khu_bi_tu_choi(self) -> None:
        bc = _Boi()
        ca = await bc.them_ca()
        nv = bc.them_nhan_vien(PHONG_A)

        with pytest.raises(PastShiftDateError):
            await bc.assign.execute(_manager(), ca.id, nv, date(2026, 7, 20))

    async def test_manager_phan_ca_phong_khac_bi_tu_choi(self) -> None:
        bc = _Boi()
        ca = await bc.them_ca(department_id=PHONG_A)
        nv = bc.them_nhan_vien(PHONG_A)

        with pytest.raises(PermissionDeniedError):
            await bc.assign.execute(_manager(PHONG_B), ca.id, nv, NGAY)

    async def test_nhan_vien_khac_phong_bi_tu_choi(self) -> None:
        bc = _Boi()
        ca = await bc.them_ca(department_id=PHONG_A)
        nv_phong_b = bc.them_nhan_vien(PHONG_B)

        with pytest.raises(PermissionDeniedError):
            await bc.assign.execute(_admin(), ca.id, nv_phong_b, NGAY)

    async def test_nhan_vien_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _Boi()
        ca = await bc.them_ca()

        with pytest.raises(NotFoundError):
            await bc.assign.execute(_manager(), ca.id, new_id(), NGAY)

    async def test_ca_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _Boi()
        nv = bc.them_nhan_vien(PHONG_A)

        with pytest.raises(NotFoundError):
            await bc.assign.execute(_manager(), new_id(), nv, NGAY)

    async def test_ca_da_vo_hieu_hoa_khong_phan_duoc(self) -> None:
        bc = _Boi()
        ca = await bc.them_ca()
        ca.deactivate(BAY_GIO)
        await bc.shift_repo.update(ca)
        nv = bc.them_nhan_vien(PHONG_A)

        with pytest.raises(NotFoundError):
            await bc.assign.execute(_manager(), ca.id, nv, NGAY)


class TestCancelShiftAssignment:
    async def test_huy_phan_ca(self) -> None:
        bc = _Boi()
        ca = await bc.them_ca()
        nv = bc.them_nhan_vien(PHONG_A)
        view = await bc.assign.execute(_manager(), ca.id, nv, NGAY)

        cancelled = await bc.cancel.execute(_manager(), view.id)

        assert cancelled.status == "CANCELLED"

    async def test_huy_roi_phan_lai_khong_bao_chong(self) -> None:
        # Buổi đã huỷ không tính chồng — phân lại đúng khung giờ đó phải được.
        bc = _Boi()
        ca = await bc.them_ca(start=time(8, 0), end=time(12, 0))
        nv = bc.them_nhan_vien(PHONG_A)
        v1 = await bc.assign.execute(_manager(), ca.id, nv, NGAY)
        await bc.cancel.execute(_manager(), v1.id)

        v2 = await bc.assign.execute(_manager(), ca.id, nv, NGAY)

        assert v2.status == "ACTIVE"


class TestListShiftAssignments:
    async def test_staff_chi_thay_ca_cua_minh(self) -> None:
        bc = _Boi()
        ca = await bc.them_ca()
        nv1 = bc.them_nhan_vien(PHONG_A)
        nv2 = bc.them_nhan_vien(PHONG_A)
        # nv2 làm ca khác giờ để không đụng nhau (khác người nên vốn không chồng).
        await bc.assign.execute(_manager(), ca.id, nv1, NGAY)
        await bc.assign.execute(_manager(), ca.id, nv2, NGAY)

        views = await bc.list.execute(_staff(nv1))

        assert {v.user_id for v in views} == {nv1}

    async def test_manager_thay_ca_ca_phong(self) -> None:
        bc = _Boi()
        ca = await bc.them_ca()
        nv1 = bc.them_nhan_vien(PHONG_A)
        nv2 = bc.them_nhan_vien(PHONG_A)
        await bc.assign.execute(_manager(), ca.id, nv1, NGAY)
        await bc.assign.execute(_manager(), ca.id, nv2, NGAY)

        views = await bc.list.execute(_manager(PHONG_A))

        assert len(views) == 2

    async def test_admin_thay_tat_ca(self) -> None:
        bc = _Boi()
        ca_a = await bc.them_ca(department_id=PHONG_A)
        ca_b = await bc.them_ca(department_id=PHONG_B)
        nv_a = bc.them_nhan_vien(PHONG_A)
        nv_b = bc.them_nhan_vien(PHONG_B)
        await bc.assign.execute(_admin(), ca_a.id, nv_a, NGAY)
        await bc.assign.execute(_admin(), ca_b.id, nv_b, NGAY)

        views = await bc.list.execute(_admin())

        assert len(views) == 2
