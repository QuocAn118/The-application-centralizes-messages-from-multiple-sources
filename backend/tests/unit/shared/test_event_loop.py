import asyncio
import sys

import pytest

from src.shared.infrastructure.event_loop import (
    cau_hinh_event_loop,
    chay_async,
    tao_event_loop,
)


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


@pytest.mark.skipif(sys.platform != "win32", reason="Chỉ áp dụng cho Windows")
def test_tao_event_loop_tren_windows_la_selector() -> None:
    """Loop trao cho thư viện ngoài phải tương thích psycopg."""
    loop = tao_event_loop()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()


def test_chay_async_tra_ve_ket_qua() -> None:
    async def cong() -> int:
        return 1 + 1

    assert chay_async(cong()) == 2


def test_chay_async_nem_lai_ngoai_le() -> None:
    async def hong() -> None:
        raise ValueError("loi trong coroutine")

    with pytest.raises(ValueError, match="loi trong coroutine"):
        chay_async(hong())


@pytest.mark.skipif(sys.platform != "win32", reason="Chỉ áp dụng cho Windows")
def test_chay_async_dung_selector_loop_bat_ke_policy() -> None:
    """Đây là điểm mấu chốt: từ Python 3.13, đặt policy KHÔNG còn đủ.

    Cố ý đặt policy Proactor trước, rồi kiểm tra ``chay_async`` vẫn cho ra
    ``SelectorEventLoop`` — nếu không, psycopg sẽ hỏng ở mọi entry point tự
    dựng loop (uvicorn dòng lệnh là ví dụ đã gặp thật).
    """
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:

        async def la_selector() -> bool:
            # isinstance chứ không so tên: lớp thật là ``_WindowsSelectorEventLoop``,
            # một lớp con — so tên sẽ đỏ dù hành vi hoàn toàn đúng.
            return isinstance(asyncio.get_running_loop(), asyncio.SelectorEventLoop)

        assert chay_async(la_selector()) is True
    finally:
        cau_hinh_event_loop()
