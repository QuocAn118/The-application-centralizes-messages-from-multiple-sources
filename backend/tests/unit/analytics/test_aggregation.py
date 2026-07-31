"""Test gộp số liệu thuần: trung bình sum/samples, gộp khối lượng, gộp hiệu suất."""

from datetime import date
from uuid import UUID

from src.modules.analytics.domain.services.aggregation import (
    gop_hieu_suat_nhan_vien,
    gop_khoi_luong,
    trung_binh,
)
from src.modules.analytics.domain.value_objects.metrics import (
    DailyAgentMetric,
    DailyConversationMetric,
)

U1 = UUID("00000000-0000-0000-0000-0000000000a1")
U2 = UUID("00000000-0000-0000-0000-0000000000a2")
D = UUID("00000000-0000-0000-0000-0000000000d1")


class TestTrungBinh:
    def test_chia_binh_thuong(self) -> None:
        assert trung_binh(100, 4) == 25.0

    def test_khong_co_mau_tra_none(self) -> None:
        assert trung_binh(0, 0) is None

    def test_mau_am_cung_tra_none(self) -> None:
        # Phòng thủ: số mẫu không bao giờ âm, nhưng không được chia gây lỗi.
        assert trung_binh(10, -1) is None


class TestGopKhoiLuong:
    def test_cong_don_nhieu_dong(self) -> None:
        rows = (
            DailyConversationMetric(
                work_date=date(2026, 7, 1),
                department_id=D,
                channel_platform="ZALO",
                inbound_count=5,
                outbound_count=3,
                opened_count=2,
                closed_count=1,
            ),
            DailyConversationMetric(
                work_date=date(2026, 7, 2),
                department_id=D,
                channel_platform="FACEBOOK",
                inbound_count=4,
                outbound_count=4,
                opened_count=1,
                closed_count=2,
            ),
        )
        v = gop_khoi_luong(rows)
        assert (v.inbound_count, v.outbound_count, v.opened_count, v.closed_count) == (9, 7, 3, 3)

    def test_rong_tra_0(self) -> None:
        v = gop_khoi_luong(())
        assert (v.inbound_count, v.closed_count) == (0, 0)


class TestGopHieuSuatNhanVien:
    def test_gop_nhieu_ngay_mot_nguoi_tinh_trung_binh_dung(self) -> None:
        # Ngày 1: 2 mẫu tổng 100s (tb 50). Ngày 2: 3 mẫu tổng 200s (tb ~66.7).
        # Gộp: 5 mẫu tổng 300s → 60.0 (khác trung bình-của-trung-bình = 58.3).
        rows = (
            DailyAgentMetric(
                work_date=date(2026, 7, 1),
                user_id=U1,
                handled_count=2,
                assigned_count=2,
                sum_first_response_seconds=100,
                first_response_samples=2,
            ),
            DailyAgentMetric(
                work_date=date(2026, 7, 2),
                user_id=U1,
                handled_count=3,
                assigned_count=1,
                sum_first_response_seconds=200,
                first_response_samples=3,
            ),
        )
        (p,) = gop_hieu_suat_nhan_vien(rows)
        assert p.user_id == U1
        assert p.handled_count == 5
        assert p.assigned_count == 3
        assert p.avg_first_response_seconds == 60.0

    def test_nhieu_nguoi_giu_thu_tu_xuat_hien(self) -> None:
        rows = (
            DailyAgentMetric(work_date=date(2026, 7, 1), user_id=U2, handled_count=1),
            DailyAgentMetric(work_date=date(2026, 7, 1), user_id=U1, handled_count=1),
        )
        ket_qua = gop_hieu_suat_nhan_vien(rows)
        assert [p.user_id for p in ket_qua] == [U2, U1]

    def test_khong_co_mau_thoi_gian_thi_avg_none(self) -> None:
        rows = (DailyAgentMetric(work_date=date(2026, 7, 1), user_id=U1, handled_count=0),)
        (p,) = gop_hieu_suat_nhan_vien(rows)
        assert p.avg_first_response_seconds is None
        assert p.avg_resolution_seconds is None

    def test_rong_tra_rong(self) -> None:
        assert gop_hieu_suat_nhan_vien(()) == ()
