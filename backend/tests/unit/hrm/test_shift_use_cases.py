from datetime import UTC, datetime, time

import pytest

from src.modules.hrm.application.actor import ActorRole, HrmActor
from src.modules.hrm.application.use_cases.shift_use_cases import (
    CreateShift,
    DeactivateShift,
    ListShifts,
    UpdateShift,
)
from src.modules.hrm.domain.entities.shift import InvalidShiftWindowError, Shift
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.hrm.fakes import FakeClock, FakeShiftRepository, FakeWorkforceDirectory

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
PHONG_A = new_id()
PHONG_B = new_id()


def _manager(department_id=PHONG_A) -> HrmActor:
    return HrmActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=department_id)


def _staff(department_id=PHONG_A) -> HrmActor:
    return HrmActor(user_id=new_id(), role=ActorRole.STAFF, department_id=department_id)


def _admin() -> HrmActor:
    return HrmActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)


class _Boi:
    def __init__(self) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.repo = FakeShiftRepository()
        self.directory = FakeWorkforceDirectory()
        self.directory.active_departments = {PHONG_A, PHONG_B}
        self.create = CreateShift(self.repo, self.directory, self.clock)
        self.update = UpdateShift(self.repo, self.clock)
        self.deactivate = DeactivateShift(self.repo, self.clock)
        self.list = ListShifts(self.repo)


class TestCreateShift:
    async def test_manager_tao_ca_phong_minh(self) -> None:
        bc = _Boi()

        view = await bc.create.execute(_manager(), PHONG_A, "Ca sáng", time(8, 0), time(12, 0))

        assert view.name == "Ca sáng"
        assert view.department_id == PHONG_A

    async def test_admin_tao_ca_moi_phong(self) -> None:
        bc = _Boi()

        view = await bc.create.execute(_admin(), PHONG_B, "Ca chiều", time(13, 0), time(17, 0))

        assert view.department_id == PHONG_B

    async def test_staff_bi_tu_choi(self) -> None:
        bc = _Boi()

        with pytest.raises(PermissionDeniedError):
            await bc.create.execute(_staff(), PHONG_A, "Ca sáng", time(8, 0), time(12, 0))

    async def test_manager_tao_ca_phong_khac_bi_tu_choi(self) -> None:
        bc = _Boi()

        with pytest.raises(PermissionDeniedError):
            await bc.create.execute(_manager(PHONG_A), PHONG_B, "Ca sáng", time(8, 0), time(12, 0))

    async def test_phong_khong_ton_tai_bi_tu_choi(self) -> None:
        bc = _Boi()
        phong_la = new_id()

        with pytest.raises(NotFoundError):
            await bc.create.execute(_admin(), phong_la, "Ca sáng", time(8, 0), time(12, 0))

    async def test_gio_nguoc_bi_tu_choi(self) -> None:
        bc = _Boi()

        with pytest.raises(InvalidShiftWindowError):
            await bc.create.execute(_manager(), PHONG_A, "Ca lỗi", time(12, 0), time(8, 0))


class TestUpdateShift:
    async def test_sua_ca_phong_minh(self) -> None:
        bc = _Boi()
        ca = Shift.create(
            department_id=PHONG_A,
            name="Ca sáng",
            start_time=time(8, 0),
            end_time=time(12, 0),
            now=BAY_GIO,
        )
        await bc.repo.add(ca)

        view = await bc.update.execute(_manager(), ca.id, "Ca sáng sớm", time(7, 0), time(11, 0))

        assert view.name == "Ca sáng sớm"
        assert view.start_time == time(7, 0)

    async def test_manager_khac_phong_khong_sua_duoc(self) -> None:
        bc = _Boi()
        ca = Shift.create(
            department_id=PHONG_A,
            name="Ca sáng",
            start_time=time(8, 0),
            end_time=time(12, 0),
            now=BAY_GIO,
        )
        await bc.repo.add(ca)

        with pytest.raises(PermissionDeniedError):
            await bc.update.execute(_manager(PHONG_B), ca.id, "X", time(7, 0), time(11, 0))

    async def test_ca_khong_ton_tai(self) -> None:
        bc = _Boi()

        with pytest.raises(NotFoundError):
            await bc.update.execute(_manager(), new_id(), "X", time(7, 0), time(11, 0))


class TestDeactivateShift:
    async def test_vo_hieu_hoa_ca(self) -> None:
        bc = _Boi()
        ca = Shift.create(
            department_id=PHONG_A,
            name="Ca sáng",
            start_time=time(8, 0),
            end_time=time(12, 0),
            now=BAY_GIO,
        )
        await bc.repo.add(ca)

        view = await bc.deactivate.execute(_manager(), ca.id)

        assert view.is_active is False


class TestListShifts:
    async def test_manager_chi_thay_phong_minh(self) -> None:
        bc = _Boi()
        await bc.repo.add(
            Shift.create(
                department_id=PHONG_A,
                name="A",
                start_time=time(8, 0),
                end_time=time(12, 0),
                now=BAY_GIO,
            )
        )
        await bc.repo.add(
            Shift.create(
                department_id=PHONG_B,
                name="B",
                start_time=time(8, 0),
                end_time=time(12, 0),
                now=BAY_GIO,
            )
        )

        views = await bc.list.execute(_manager(PHONG_A))

        assert {v.department_id for v in views} == {PHONG_A}

    async def test_admin_thay_tat_ca(self) -> None:
        bc = _Boi()
        await bc.repo.add(
            Shift.create(
                department_id=PHONG_A,
                name="A",
                start_time=time(8, 0),
                end_time=time(12, 0),
                now=BAY_GIO,
            )
        )
        await bc.repo.add(
            Shift.create(
                department_id=PHONG_B,
                name="B",
                start_time=time(8, 0),
                end_time=time(12, 0),
                now=BAY_GIO,
            )
        )

        views = await bc.list.execute(_admin())

        assert len(views) == 2
