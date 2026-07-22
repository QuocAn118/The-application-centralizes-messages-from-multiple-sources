"""Cấu hình event loop cho từng nền tảng."""

import asyncio
import sys


def cau_hinh_event_loop() -> None:
    """Chuyển Windows sang ``SelectorEventLoop`` trước khi mở kết nối async.

    Từ Python 3.8, event loop mặc định của Windows là ``ProactorEventLoop``.
    psycopg từ chối chạy trên nó và ném ``InterfaceError: Psycopg cannot use
    the 'ProactorEventLoop' to run in async mode``. Đây là hạn chế đã biết của
    driver, không phải lỗi cấu hình.

    Mọi entry point chạy code async phải gọi hàm này **trước khi** tạo engine:
    ``tests/conftest.py``, ``migrations/env.py``, ``src/main.py``, và các script
    trong ``scripts/``. Gọi nhiều lần không gây hại.

    Trên Linux và macOS hàm này không làm gì — nơi triển khai thật sẽ chạy
    Linux, nên chi phí bằng không ở môi trường sản xuất.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
