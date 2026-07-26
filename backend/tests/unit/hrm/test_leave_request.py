from datetime import UTC, date, datetime

import pytest

from src.modules.hrm.domain.entities.leave_request import (
    EmptyReasonError,
    InvalidLeavePeriodError,
    LeaveRequest,
    MissingLeavePeriodError,
    MissingRejectionReasonError,
    RequestNotPendingError,
)
from src.modules.hrm.domain.value_objects.request_kind import (
    RequestStatus,
    RequestType,
)
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
NGUOI_GUI = new_id()
PHONG = new_id()


def _don_nghi_phep(
    *, leave_start=date(2026, 8, 10), leave_end=date(2026, 8, 12), reason="Việc gia đình"
) -> LeaveRequest:
    return LeaveRequest.submit(
        requester_id=NGUOI_GUI,
        department_id=PHONG,
        request_type=RequestType.NGHI_PHEP,
        reason=reason,
        leave_start=leave_start,
        leave_end=leave_end,
        now=BAY_GIO,
    )


def _don_khac() -> LeaveRequest:
    return LeaveRequest.submit(
        requester_id=NGUOI_GUI,
        department_id=PHONG,
        request_type=RequestType.TANG_LUONG,
        reason="Đề xuất tăng lương",
        now=BAY_GIO,
    )


class TestGuiDon:
    def test_gui_don_nghi_phep_hop_le(self) -> None:
        don = _don_nghi_phep()

        assert don.status is RequestStatus.CHO_DUYET
        assert don.request_type is RequestType.NGHI_PHEP
        assert don.leave_start == date(2026, 8, 10)
        assert don.decided_by is None

    def test_gui_don_tang_luong_khong_can_khoang_thoi_gian(self) -> None:
        don = _don_khac()

        assert don.status is RequestStatus.CHO_DUYET
        assert don.leave_start is None
        assert don.leave_end is None

    def test_ly_do_rong_bi_tu_choi(self) -> None:
        with pytest.raises(EmptyReasonError):
            _don_nghi_phep(reason="   ")

    def test_nghi_phep_thieu_khoang_thoi_gian_bi_tu_choi(self) -> None:
        with pytest.raises(MissingLeavePeriodError):
            LeaveRequest.submit(
                requester_id=NGUOI_GUI,
                department_id=PHONG,
                request_type=RequestType.NGHI_PHEP,
                reason="Nghỉ",
                now=BAY_GIO,
            )

    def test_nghi_phep_ngay_ket_thuc_truoc_ngay_bat_dau_bi_tu_choi(self) -> None:
        with pytest.raises(InvalidLeavePeriodError):
            _don_nghi_phep(leave_start=date(2026, 8, 12), leave_end=date(2026, 8, 10))

    def test_nghi_phep_ngay_qua_khu_bi_tu_choi(self) -> None:
        # now = 2026-08-01
        with pytest.raises(InvalidLeavePeriodError):
            _don_nghi_phep(leave_start=date(2026, 7, 20), leave_end=date(2026, 7, 25))

    def test_loai_khac_ma_lo_truyen_khoang_thoi_gian_thi_bo_qua(self) -> None:
        don = LeaveRequest.submit(
            requester_id=NGUOI_GUI,
            department_id=PHONG,
            request_type=RequestType.KHAC,
            reason="Ghi chú",
            leave_start=date(2026, 8, 10),
            leave_end=date(2026, 8, 12),
            now=BAY_GIO,
        )

        assert don.leave_start is None
        assert don.leave_end is None


class TestDuyet:
    def test_duyet_don_cho_duyet(self) -> None:
        don = _don_nghi_phep()
        nguoi_duyet = new_id()

        don.approve(nguoi_duyet, BAY_GIO)

        assert don.status is RequestStatus.DA_DUYET
        assert don.decided_by == nguoi_duyet
        assert don.decided_at == BAY_GIO

    def test_khong_duyet_lai_don_da_duyet(self) -> None:
        don = _don_nghi_phep()
        don.approve(new_id(), BAY_GIO)

        with pytest.raises(RequestNotPendingError):
            don.approve(new_id(), BAY_GIO)

    def test_khong_duyet_don_da_tu_choi(self) -> None:
        don = _don_nghi_phep()
        don.reject(new_id(), "Không hợp lý", BAY_GIO)

        with pytest.raises(RequestNotPendingError):
            don.approve(new_id(), BAY_GIO)


class TestTuChoi:
    def test_tu_choi_kem_ly_do(self) -> None:
        don = _don_nghi_phep()
        nguoi_duyet = new_id()

        don.reject(nguoi_duyet, "Đang cao điểm, không duyệt", BAY_GIO)

        assert don.status is RequestStatus.TU_CHOI
        assert don.decision_reason == "Đang cao điểm, không duyệt"
        assert don.decided_by == nguoi_duyet

    def test_tu_choi_khong_ly_do_bi_chan(self) -> None:
        don = _don_nghi_phep()

        with pytest.raises(MissingRejectionReasonError):
            don.reject(new_id(), "   ", BAY_GIO)


class TestThuHoi:
    def test_thu_hoi_don_cho_duyet(self) -> None:
        don = _don_nghi_phep()

        don.cancel(BAY_GIO)

        assert don.status is RequestStatus.DA_HUY

    def test_khong_thu_hoi_don_da_duyet(self) -> None:
        don = _don_nghi_phep()
        don.approve(new_id(), BAY_GIO)

        with pytest.raises(RequestNotPendingError):
            don.cancel(BAY_GIO)
