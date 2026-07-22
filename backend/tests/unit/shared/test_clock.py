from datetime import UTC, datetime

from src.shared.infrastructure.clock import SystemClock


def test_tra_ve_thoi_diem_co_kem_mui_gio() -> None:
    """Thời điểm không kèm múi giờ sẽ làm hỏng mọi phép so sánh với cột
    ``timestamptz`` đọc từ cơ sở dữ liệu."""
    bay_gio = SystemClock().now()

    assert bay_gio.tzinfo is not None
    assert bay_gio.utcoffset() == UTC.utcoffset(None)


def test_thoi_gian_khong_lui_ve_qua_khu() -> None:
    truoc = SystemClock().now()
    sau = SystemClock().now()

    assert sau >= truoc


def test_gan_voi_thoi_gian_he_thong() -> None:
    lech = abs((SystemClock().now() - datetime.now(UTC)).total_seconds())

    assert lech < 5
