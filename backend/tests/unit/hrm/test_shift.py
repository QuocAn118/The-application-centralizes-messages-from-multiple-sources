from datetime import UTC, date, datetime, time

import pytest

from src.modules.hrm.domain.entities.shift import (
    EmptyShiftNameError,
    InvalidShiftWindowError,
    Shift,
)
from src.modules.hrm.domain.entities.shift_assignment import (
    PastShiftDateError,
    ShiftAssignment,
)
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
PHONG = new_id()


class TestShift:
    def test_tao_ca_hop_le(self) -> None:
        ca = Shift.create(
            department_id=PHONG,
            name="Ca sáng",
            start_time=time(8, 0),
            end_time=time(12, 0),
            now=BAY_GIO,
        )

        assert ca.name == "Ca sáng"
        assert ca.department_id == PHONG
        assert ca.is_active is True

    def test_ten_ca_bi_cat_khoang_trang(self) -> None:
        ca = Shift.create(
            department_id=PHONG,
            name="  Ca chiều  ",
            start_time=time(13, 0),
            end_time=time(17, 0),
            now=BAY_GIO,
        )

        assert ca.name == "Ca chiều"

    def test_ten_rong_bi_tu_choi(self) -> None:
        with pytest.raises(EmptyShiftNameError):
            Shift.create(
                department_id=PHONG,
                name="   ",
                start_time=time(8, 0),
                end_time=time(12, 0),
                now=BAY_GIO,
            )

    def test_gio_ket_thuc_khong_sau_gio_bat_dau_bi_tu_choi(self) -> None:
        with pytest.raises(InvalidShiftWindowError):
            Shift.create(
                department_id=PHONG,
                name="Ca lỗi",
                start_time=time(12, 0),
                end_time=time(8, 0),
                now=BAY_GIO,
            )

    def test_gio_bang_nhau_bi_tu_choi(self) -> None:
        with pytest.raises(InvalidShiftWindowError):
            Shift.create(
                department_id=PHONG,
                name="Ca rỗng thời lượng",
                start_time=time(8, 0),
                end_time=time(8, 0),
                now=BAY_GIO,
            )

    def test_sua_khung_gio_van_giu_bat_bien(self) -> None:
        ca = Shift.create(
            department_id=PHONG,
            name="Ca sáng",
            start_time=time(8, 0),
            end_time=time(12, 0),
            now=BAY_GIO,
        )

        with pytest.raises(InvalidShiftWindowError):
            ca.update_window("Ca sáng", time(12, 0), time(8, 0), BAY_GIO)

    def test_deactivate(self) -> None:
        ca = Shift.create(
            department_id=PHONG,
            name="Ca sáng",
            start_time=time(8, 0),
            end_time=time(12, 0),
            now=BAY_GIO,
        )
        ca.deactivate(BAY_GIO)

        assert ca.is_active is False


def _phan_ca(user_id, work_date, start_time, end_time, *, department_id=PHONG) -> ShiftAssignment:
    return ShiftAssignment.assign(
        shift_id=new_id(),
        user_id=user_id,
        department_id=department_id,
        work_date=work_date,
        start_time=start_time,
        end_time=end_time,
        now=BAY_GIO,
    )


class TestShiftAssignment:
    def test_phan_ca_hop_le(self) -> None:
        nv = new_id()
        pc = _phan_ca(nv, date(2026, 8, 5), time(8, 0), time(12, 0))

        assert pc.user_id == nv
        assert pc.is_active is True

    def test_phan_ca_hom_nay_hop_le(self) -> None:
        # now = 2026-08-01; phân ca đúng ngày hôm nay vẫn được.
        pc = _phan_ca(new_id(), date(2026, 8, 1), time(8, 0), time(12, 0))

        assert pc.is_active is True

    def test_phan_ca_ngay_qua_khu_bi_tu_choi(self) -> None:
        with pytest.raises(PastShiftDateError):
            _phan_ca(new_id(), date(2026, 7, 31), time(8, 0), time(12, 0))

    def test_huy_phan_ca(self) -> None:
        pc = _phan_ca(new_id(), date(2026, 8, 5), time(8, 0), time(12, 0))
        pc.cancel(BAY_GIO)

        assert pc.is_active is False


class TestChongCa:
    def test_hai_ca_giam_gio_cung_ngay_cung_nguoi_la_chong(self) -> None:
        nv = new_id()
        a = _phan_ca(nv, date(2026, 8, 5), time(8, 0), time(12, 0))
        b = _phan_ca(nv, date(2026, 8, 5), time(11, 0), time(15, 0))

        assert a.overlaps(b) is True
        assert b.overlaps(a) is True

    def test_hai_ca_ke_nhau_khong_chong(self) -> None:
        # [8,12) và [12,16) chạm biên nhưng không giao — không tính chồng.
        nv = new_id()
        a = _phan_ca(nv, date(2026, 8, 5), time(8, 0), time(12, 0))
        b = _phan_ca(nv, date(2026, 8, 5), time(12, 0), time(16, 0))

        assert a.overlaps(b) is False

    def test_khac_ngay_khong_chong(self) -> None:
        nv = new_id()
        a = _phan_ca(nv, date(2026, 8, 5), time(8, 0), time(12, 0))
        b = _phan_ca(nv, date(2026, 8, 6), time(8, 0), time(12, 0))

        assert a.overlaps(b) is False

    def test_khac_nguoi_khong_chong(self) -> None:
        a = _phan_ca(new_id(), date(2026, 8, 5), time(8, 0), time(12, 0))
        b = _phan_ca(new_id(), date(2026, 8, 5), time(8, 0), time(12, 0))

        assert a.overlaps(b) is False

    def test_ca_da_huy_khong_tinh_chong(self) -> None:
        nv = new_id()
        a = _phan_ca(nv, date(2026, 8, 5), time(8, 0), time(12, 0))
        b = _phan_ca(nv, date(2026, 8, 5), time(9, 0), time(11, 0))
        b.cancel(BAY_GIO)

        assert a.overlaps(b) is False
