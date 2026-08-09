"""Cấu hình event loop cho từng nền tảng."""

import asyncio
import selectors
import sys
from collections.abc import Coroutine
from typing import Any


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

    **Giới hạn:** đặt policy chỉ có tác dụng với code sau đó gọi ``asyncio.run``
    hay ``get_event_loop``. Chương trình nào TỰ dựng loop (uvicorn khi chạy bằng
    lệnh ``uvicorn`` ở dòng lệnh) sẽ bỏ qua policy này — xem ``chay_async``.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def tao_event_loop() -> asyncio.AbstractEventLoop:
    """Tạo một event loop tương thích psycopg cho nền tảng hiện tại.

    Trên Windows luôn là ``SelectorEventLoop``, bất kể policy đang là gì. Dùng
    khi cần trao loop cho một thư viện tự quản vòng đời loop.
    """
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop(selectors.SelectSelector())
    return asyncio.new_event_loop()


def chay_async[T](coro: Coroutine[Any, Any, T]) -> T:
    """Chạy ``coro`` trên một event loop chắc chắn tương thích psycopg.

    Vì sao cần, thay vì chỉ ``cau_hinh_event_loop()`` rồi ``asyncio.run``:
    từ Python 3.12 ``asyncio.run`` nhận ``loop_factory``, và từ 3.13 việc đặt
    policy không còn đủ trong mọi trường hợp — chương trình tự dựng loop (như
    uvicorn chạy từ dòng lệnh) sẽ dùng ``ProactorEventLoop`` mặc định của
    Windows và psycopg lập tức hỏng. Truyền thẳng loop_factory là cách duy nhất
    chắc chắn.

    Dùng cho mọi entry point async tự chạy: script, và lệnh khởi động server ở
    ``scripts/run_server.py``.
    """
    cau_hinh_event_loop()
    if sys.platform == "win32":
        return asyncio.run(coro, loop_factory=tao_event_loop)
    return asyncio.run(coro)
