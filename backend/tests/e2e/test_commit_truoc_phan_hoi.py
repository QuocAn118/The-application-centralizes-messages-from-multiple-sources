"""Giao dịch của request phải commit XONG trước khi phản hồi rời server.

FastAPI mặc định chạy phần sau ``yield`` của dependency SAU khi gửi phản hồi, nên
client có thể nhận 201 khi dữ liệu chưa lưu, và commit lỗi vẫn thành 200 im lặng.
``DbSession`` dùng ``scope="function"`` để commit chạy trước khi gửi.

httpx với ``ASGITransport`` chờ app chạy hết mới trả, nên không thấy được thứ tự
này — test (a) gọi app ASGI trực tiếp và kiểm DB ĐÚNG lúc app gửi dòng trạng thái.
"""

import asyncio
import json
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from tests.e2e.test_user_api import _bearer, _tao_admin, _token

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


async def test_du_lieu_da_luu_khi_phan_hoi_bat_dau(
    app_test: Any, client: AsyncClient, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _tao_admin(engine)
    token = await _token(client, "admin@congty.vn")

    # Commit chậm để thứ tự không phụ thuộc may rủi: nếu phản hồi đi trước commit,
    # lúc kiểm DB chắc chắn còn chưa có dòng.
    commit_goc = AsyncSession.commit

    async def commit_cham(self: AsyncSession) -> None:
        await asyncio.sleep(0.3)
        await commit_goc(self)

    monkeypatch.setattr(AsyncSession, "commit", commit_cham)
    than = json.dumps({"name": "Phong commit truoc"}).encode()

    luc_gui: dict[str, Any] = {}

    async def nhan() -> dict[str, Any]:
        return {"type": "http.request", "body": than, "more_body": False}

    async def gui(thong_diep: dict[str, Any]) -> None:
        if thong_diep["type"] == "http.response.start":
            luc_gui["status"] = thong_diep["status"]
            async with engine.connect() as conn:
                luc_gui["so_dong"] = (
                    await conn.execute(
                        text("SELECT count(*) FROM departments WHERE name = 'Phong commit truoc'")
                    )
                ).scalar_one()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/departments",
        "raw_path": b"/api/v1/departments",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"test"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(than)).encode()),
            (b"authorization", f"Bearer {token}".encode()),
        ],
        "client": ("127.0.0.1", 1234),
        "server": ("test", 80),
    }
    await app_test(scope, nhan, gui)
    monkeypatch.undo()

    assert luc_gui["status"] == 201
    assert luc_gui["so_dong"] == 1, "Phản hồi 201 đã gửi khi dữ liệu chưa commit"


async def test_commit_loi_thi_client_nhan_5xx(
    app_test: Any, client: AsyncClient, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _tao_admin(engine)
    token = await _token(client, "admin@congty.vn")

    async def commit_hong(self: AsyncSession) -> None:
        raise RuntimeError("giả lập commit lỗi")

    monkeypatch.setattr(AsyncSession, "commit", commit_hong)
    async with AsyncClient(
        transport=ASGITransport(app=app_test, raise_app_exceptions=False), base_url="http://test"
    ) as c:
        phan_hoi = await c.post(
            "/api/v1/departments", json={"name": "Phong commit loi"}, headers=_bearer(token)
        )
    monkeypatch.undo()

    assert phan_hoi.status_code >= 500
    async with engine.connect() as conn:
        so_dong = (
            await conn.execute(
                text("SELECT count(*) FROM departments WHERE name = 'Phong commit loi'")
            )
        ).scalar_one()
    assert so_dong == 0
