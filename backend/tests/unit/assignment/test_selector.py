"""Test bộ chọn nhân viên — chuỗi tiêu chí theo thứ tự ưu tiên.

Mỗi test cô lập một tầng phá hoà: các tín hiệu trên đều bằng nhau để chỉ tầng
đang xét quyết định, xác nhận đúng thứ tự ca → tải → KPI → round-robin.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from src.modules.assignment.domain.services.selector import chon_nhan_vien
from src.modules.assignment.domain.value_objects.candidate import AgentCandidate

A = UUID("00000000-0000-0000-0000-0000000000a1")
B = UUID("00000000-0000-0000-0000-0000000000b2")
C = UUID("00000000-0000-0000-0000-0000000000c3")


def _cand(
    user_id: UUID,
    on_shift: bool = True,
    open_load: int = 0,
    kpi_percent: Decimal | None = Decimal("100"),
    last_assigned_at: datetime | None = datetime(2026, 1, 1, tzinfo=UTC),
) -> AgentCandidate:
    return AgentCandidate(
        user_id=user_id,
        on_shift=on_shift,
        open_load=open_load,
        kpi_percent=kpi_percent,
        last_assigned_at=last_assigned_at,
    )


class TestChonNhanVien:
    def test_rong_thi_none(self) -> None:
        assert chon_nhan_vien(()) is None

    def test_khong_ai_trong_ca_thi_none(self) -> None:
        assert chon_nhan_vien((_cand(A, on_shift=False), _cand(B, on_shift=False))) is None

    def test_loc_ngoai_ca_truoc_moi_tieu_chi(self) -> None:
        # B ngoài ca dù tải 0; A trong ca dù tải cao hơn -> chọn A.
        chon = chon_nhan_vien((_cand(A, open_load=5), _cand(B, on_shift=False, open_load=0)))
        assert chon == A

    def test_uu_tien_tai_thap_nhat(self) -> None:
        chon = chon_nhan_vien((_cand(A, open_load=3), _cand(B, open_load=1), _cand(C, open_load=2)))
        assert chon == B

    def test_hoa_tai_thi_kpi_thap_hon_thang(self) -> None:
        # Cùng tải; B đạt KPI thấp hơn -> ưu tiên B (chia việc để đạt target).
        chon = chon_nhan_vien(
            (
                _cand(A, open_load=1, kpi_percent=Decimal("120")),
                _cand(B, open_load=1, kpi_percent=Decimal("60")),
            )
        )
        assert chon == B

    def test_kpi_none_xem_nhu_thap_nhat(self) -> None:
        # B chưa có dữ liệu KPI -> xem như thấp nhất -> ưu tiên B.
        chon = chon_nhan_vien(
            (
                _cand(A, open_load=1, kpi_percent=Decimal("10")),
                _cand(B, open_load=1, kpi_percent=None),
            )
        )
        assert chon == B

    def test_hoa_kpi_thi_round_robin_cu_nhat_thang(self) -> None:
        # Cùng tải + KPI; A được gán lâu hơn -> A tới lượt.
        chon = chon_nhan_vien(
            (
                _cand(
                    A,
                    open_load=1,
                    kpi_percent=Decimal("80"),
                    last_assigned_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
                _cand(
                    B,
                    open_load=1,
                    kpi_percent=Decimal("80"),
                    last_assigned_at=datetime(2026, 6, 1, tzinfo=UTC),
                ),
            )
        )
        assert chon == A

    def test_chua_tung_nhan_thi_round_robin_truoc_het(self) -> None:
        # B chưa từng được gán (None) -> đứng trước theo round-robin.
        chon = chon_nhan_vien(
            (
                _cand(
                    A,
                    open_load=1,
                    kpi_percent=Decimal("80"),
                    last_assigned_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
                _cand(B, open_load=1, kpi_percent=Decimal("80"), last_assigned_at=None),
            )
        )
        assert chon == B
