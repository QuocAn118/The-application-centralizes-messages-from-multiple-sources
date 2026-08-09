"""Khởi động API server.

Dùng script này thay cho lệnh ``uvicorn src.main:app`` trên Windows: uvicorn ở
dòng lệnh tự dựng event loop trước khi nạp ứng dụng, nên bỏ qua policy mà
``cau_hinh_event_loop()`` đặt — psycopg gặp ``ProactorEventLoop`` và mọi request
chạm cơ sở dữ liệu trả 500. Ở đây loop được truyền thẳng nên không có khe hở đó.

Chạy:
    uv run python -m scripts.run_server
    uv run python -m scripts.run_server --port 8001 --reload
"""

import argparse

import uvicorn

from src.shared.infrastructure.event_loop import chay_async


def main() -> int:
    bo_doc = argparse.ArgumentParser(description="Khởi động OmniChat API.")
    bo_doc.add_argument("--host", default="127.0.0.1")
    bo_doc.add_argument("--port", type=int, default=8000)
    bo_doc.add_argument("--log-level", default="info")
    bo_doc.add_argument(
        "--reload",
        action="store_true",
        help="Tự nạp lại khi mã nguồn đổi (chỉ dùng khi phát triển).",
    )
    tham_so = bo_doc.parse_args()

    if tham_so.reload:
        # Chế độ reload cần uvicorn tự quản tiến trình con, không dùng chung
        # loop với tiến trình cha — truyền chuỗi import và để uvicorn lo.
        uvicorn.run(
            "src.main:app",
            host=tham_so.host,
            port=tham_so.port,
            log_level=tham_so.log_level,
            reload=True,
            loop="asyncio",
        )
        return 0

    from src.main import app

    cau_hinh = uvicorn.Config(
        app,
        host=tham_so.host,
        port=tham_so.port,
        log_level=tham_so.log_level,
    )
    chay_async(uvicorn.Server(cau_hinh).serve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
