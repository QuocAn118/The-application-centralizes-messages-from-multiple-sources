import asyncio
import sys

import pytest

from src.shared.infrastructure.event_loop import cau_hinh_event_loop


@pytest.mark.skipif(sys.platform != "win32", reason="Chỉ áp dụng cho Windows")
def test_tren_windows_chon_selector_event_loop() -> None:
    """psycopg từ chối ProactorEventLoop — nếu test này đỏ thì mọi test chạm
    cơ sở dữ liệu cũng sẽ đỏ theo."""
    cau_hinh_event_loop()

    assert isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsSelectorEventLoopPolicy)


@pytest.mark.skipif(sys.platform == "win32", reason="Chỉ áp dụng cho Linux/macOS")
def test_ngoai_windows_khong_doi_gi() -> None:
    truoc = asyncio.get_event_loop_policy()

    cau_hinh_event_loop()

    assert asyncio.get_event_loop_policy() is truoc


def test_goi_nhieu_lan_khong_gay_loi() -> None:
    cau_hinh_event_loop()
    cau_hinh_event_loop()
