from datetime import UTC, datetime

import pytest

from src.shared.infrastructure.rate_limiter import (
    InMemoryRateLimiter,
    RateLimitExceededError,
)
from tests.unit.identity.fakes import FakeClock

BAY_GIO = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


def _tao(max_attempts: int = 3, window_seconds: int = 300) -> tuple[InMemoryRateLimiter, FakeClock]:
    dong_ho = FakeClock(BAY_GIO)
    return InMemoryRateLimiter(max_attempts, window_seconds, dong_ho), dong_ho


class TestNguongThuLai:
    def test_cho_phep_trong_gioi_han(self) -> None:
        gioi_han, _ = _tao(max_attempts=3)

        for _ in range(3):
            gioi_han.check("a@congty.vn")

    def test_vuot_gioi_han_thi_chan(self) -> None:
        gioi_han, _ = _tao(max_attempts=3)
        for _ in range(3):
            gioi_han.check("a@congty.vn")

        with pytest.raises(RateLimitExceededError):
            gioi_han.check("a@congty.vn")

    def test_cac_khoa_khac_nhau_dem_rieng(self) -> None:
        gioi_han, _ = _tao(max_attempts=2)
        gioi_han.check("a@congty.vn")
        gioi_han.check("a@congty.vn")

        gioi_han.check("b@congty.vn")

    def test_bo_dem_duoc_xoa_sau_khi_het_cua_so(self) -> None:
        gioi_han, dong_ho = _tao(max_attempts=2, window_seconds=300)
        gioi_han.check("a@congty.vn")
        gioi_han.check("a@congty.vn")

        dong_ho.advance(seconds=301)

        gioi_han.check("a@congty.vn")

    def test_van_chan_khi_chua_het_cua_so(self) -> None:
        gioi_han, dong_ho = _tao(max_attempts=2, window_seconds=300)
        gioi_han.check("a@congty.vn")
        gioi_han.check("a@congty.vn")

        dong_ho.advance(seconds=299)

        with pytest.raises(RateLimitExceededError):
            gioi_han.check("a@congty.vn")

    def test_bao_so_giay_can_cho(self) -> None:
        gioi_han, _ = _tao(max_attempts=1, window_seconds=300)
        gioi_han.check("a@congty.vn")

        with pytest.raises(RateLimitExceededError) as loi:
            gioi_han.check("a@congty.vn")

        assert loi.value.retry_after_seconds > 0
        assert loi.value.retry_after_seconds <= 300


class TestXoaBoDem:
    def test_dang_nhap_thanh_cong_xoa_bo_dem(self) -> None:
        """Người dùng gõ nhầm vài lần rồi đăng nhập được không nên bị phạt tiếp."""
        gioi_han, _ = _tao(max_attempts=3)
        gioi_han.check("a@congty.vn")
        gioi_han.check("a@congty.vn")

        gioi_han.reset("a@congty.vn")

        for _ in range(3):
            gioi_han.check("a@congty.vn")

    def test_xoa_khoa_khong_ton_tai_khong_gay_loi(self) -> None:
        gioi_han, _ = _tao()

        gioi_han.reset("chua-bao-gio-goi@congty.vn")


class TestDonRac:
    def test_khong_giu_mai_cac_khoa_da_het_han(self) -> None:
        """Bộ đếm phải được dọn, nếu không bộ nhớ sẽ phình theo số email bị dò."""
        gioi_han, dong_ho = _tao(max_attempts=5, window_seconds=60)
        for i in range(100):
            gioi_han.check(f"dothu{i}@congty.vn")

        dong_ho.advance(seconds=61)
        gioi_han.check("kich-hoat-don-rac@congty.vn")

        assert gioi_han.so_khoa_dang_giu() <= 2
