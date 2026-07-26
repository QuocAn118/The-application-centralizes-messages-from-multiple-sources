"""E2E cho WebSocket realtime: tin mới → client nhận tín hiệu.

Dùng TestClient (starlette) vì httpx.ASGITransport không hỗ trợ WebSocket.
Test đồng bộ (không async) vì TestClient tự chạy vòng lặp riêng; ``don_du_lieu``
autouse vẫn dọn bảng sau mỗi test.
"""

import hashlib
import json

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.main import create_app
from src.modules.inbox.infrastructure.channels.registry import ChannelAdapterRegistry
from src.modules.inbox.infrastructure.channels.zalo_adapter import ZaloAdapter

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU_ADMIN = "MatKhauAdmin123"
ZALO_APP_ID = "app_ws"
ZALO_OA_SECRET = "oa_ws"


def _mock_client() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"message_id": "x"}})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _app(engine: AsyncEngine):  # type: ignore[no-untyped-def]
    """App trỏ vào DB test, adapter dùng bí mật đã biết + client giả.

    Ghi đè ``session_factory`` *sau* khi TestClient chạy lifespan bằng cách gắn
    một dependency-free state; TestClient gọi lifespan nên ta ghi đè trong khối
    ``with`` bên dưới, không ở đây.
    """
    app = create_app()
    app.state.inbox_adapter_registry = ChannelAdapterRegistry(
        [ZaloAdapter(ZALO_APP_ID, ZALO_OA_SECRET, client_factory=_mock_client)]
    )
    return app


def _tro_vao_db_test(app, engine: AsyncEngine) -> None:  # type: ignore[no-untyped-def]
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


async def _tao_admin(engine: AsyncEngine) -> None:
    from src.modules.identity.infrastructure.security.password_hasher import (
        BcryptPasswordHasher,
    )
    from src.shared.domain.identifiers import new_id

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, full_name, phone, role, "
                "department_id, is_active, must_change_password, last_login_at, "
                "created_at, updated_at) VALUES (:id, 'admin@congty.vn', :hash, "
                "'Admin', NULL, 'ADMIN', NULL, true, false, NULL, now(), now())"
            ),
            {"id": new_id(), "hash": BcryptPasswordHasher(rounds=4).hash(MAT_KHAU_ADMIN)},
        )


def _ky(raw: bytes) -> str:
    ts = str(json.loads(raw)["timestamp"])
    chuoi = ZALO_APP_ID.encode() + raw + ts.encode() + ZALO_OA_SECRET.encode()
    return "mac=" + hashlib.sha256(chuoi).hexdigest()


def _webhook(oa_id: str) -> bytes:
    return json.dumps(
        {
            "app_id": ZALO_APP_ID,
            "oa_id": oa_id,
            "timestamp": "1690000000000",
            "event_name": "user_send_text",
            "sender": {"id": "khach_ws"},
            "message": {"msg_id": "m_ws", "text": "co ai khong"},
        }
    ).encode()


def test_tin_moi_day_tin_hieu_toi_client(engine: AsyncEngine) -> None:
    import anyio

    anyio.run(_tao_admin, engine)

    app = _app(engine)
    with TestClient(app) as client:
        _tro_vao_db_test(app, engine)

        dn = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU_ADMIN},
        )
        token = dn.json()["access_token"]

        client.post(
            "/api/v1/channels",
            json={
                "platform": "ZALO",
                "external_channel_id": "oa_ws",
                "name": "OA",
                "credential": "t",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        with client.websocket_connect(f"/ws/inbox?token={token}") as ws:
            raw = _webhook("oa_ws")
            r = client.post(
                "/api/v1/webhooks/ZALO",
                content=raw,
                headers={"X-ZEvent-Signature": _ky(raw)},
            )
            assert r.status_code == 200

            tin_hieu = ws.receive_json()
            assert tin_hieu["change"] == "new_message"
            assert "conversation_id" in tin_hieu


def test_ws_thieu_token_bi_dong(engine: AsyncEngine) -> None:
    app = _app(engine)
    with TestClient(app) as client:
        _tro_vao_db_test(app, engine)
        with pytest.raises(WebSocketDisconnect):  # noqa: SIM117
            with client.websocket_connect("/ws/inbox") as ws:
                ws.receive_json()
