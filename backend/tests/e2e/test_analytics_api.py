"""E2E cho #5 Analytics: rollup incremental qua webhook/reply/close + báo cáo JSON.

Đi qua HTTP thật (ASGI) + PostgreSQL thật. Chuỗi: khách nhắn (webhook) → +1
inbound rollup; Admin phân phòng + nhân viên trả lời → +1 outbound; đóng → +1
closed/handled. Rồi gọi báo cáo, kiểm phân quyền (Staff 403, Manager ép phòng).
"""

import hashlib
import json
from datetime import date

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.modules.inbox.infrastructure.channels.registry import ChannelAdapterRegistry
from src.modules.inbox.infrastructure.channels.zalo_adapter import ZaloAdapter

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU = "MatKhau123ABC"
ZALO_APP_ID = "app_test"
ZALO_OA_SECRET = "oa_secret_test"
HOM_NAY = date.today().isoformat()


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _mock_adapter_client() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        # Zalo send_message đọc resp.json() → phải trả JSON hợp lệ (dạng phản hồi
        # gửi tin thành công của Zalo OA).
        return httpx.Response(
            200, json={"error": 0, "message": "Success", "data": {"message_id": "x"}}
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def app_an(app_test):  # type: ignore[no-untyped-def]
    app_test.state.inbox_adapter_registry = ChannelAdapterRegistry(
        [ZaloAdapter(ZALO_APP_ID, ZALO_OA_SECRET, client_factory=_mock_adapter_client)]
    )
    return app_test


@pytest.fixture
async def client_an(app_an):  # type: ignore[no-untyped-def]
    async with AsyncClient(transport=ASGITransport(app=app_an), base_url="http://test") as ac:
        yield ac


async def _seed(engine: AsyncEngine) -> dict[str, str]:
    from src.modules.identity.infrastructure.security.password_hasher import (
        BcryptPasswordHasher,
    )
    from src.shared.domain.identifiers import new_id

    h = BcryptPasswordHasher(rounds=4).hash(MAT_KHAU)
    ids = {
        "phong": str(new_id()),
        "phong2": str(new_id()),
        "admin": str(new_id()),
        "manager": str(new_id()),
        "staff": str(new_id()),
        "manager2": str(new_id()),
    }
    async with engine.begin() as conn:
        for key, ten in (("phong", "KD"), ("phong2", "KT")):
            await conn.execute(
                text(
                    "INSERT INTO departments (id, name, description, is_active, "
                    "created_at, updated_at) VALUES (:id, :ten, NULL, true, now(), now())"
                ),
                {"id": ids[key], "ten": ten},
            )

        async def them(uid: str, email: str, role: str, dept: str | None) -> None:
            await conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, full_name, phone, role, "
                    "department_id, is_active, must_change_password, last_login_at, "
                    "created_at, updated_at) VALUES (:id, :email, :h, :name, NULL, :role, "
                    ":dept, true, false, NULL, now(), now())"
                ),
                {"id": uid, "email": email, "h": h, "name": role, "role": role, "dept": dept},
            )

        await them(ids["admin"], "admin@x.vn", "ADMIN", None)
        await them(ids["manager"], "manager@x.vn", "MANAGER", ids["phong"])
        await them(ids["staff"], "staff@x.vn", "STAFF", ids["phong"])
        await them(ids["manager2"], "manager2@x.vn", "MANAGER", ids["phong2"])
    return ids


async def _login(client: AsyncClient, email: str) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": MAT_KHAU})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _ky_zalo(raw: bytes) -> str:
    ts = str(json.loads(raw)["timestamp"])
    chuoi = ZALO_APP_ID.encode() + raw + ts.encode() + ZALO_OA_SECRET.encode()
    return "mac=" + hashlib.sha256(chuoi).hexdigest()


def _webhook(oa: str, sender: str, msg: str, txt: str) -> bytes:
    return json.dumps(
        {
            "app_id": ZALO_APP_ID,
            "oa_id": oa,
            "timestamp": "1690000000000",
            "event_name": "user_send_text",
            "sender": {"id": sender},
            "message": {"msg_id": msg, "text": txt},
        }
    ).encode()


async def _khach_nhan(client: AsyncClient, oa: str, sender: str, msg: str) -> None:
    raw = _webhook(oa, sender, msg, "toi can ho tro")
    r = await client.post(
        "/api/v1/webhooks/ZALO", content=raw, headers={"X-ZEvent-Signature": _ky_zalo(raw)}
    )
    assert r.status_code == 200, r.text


async def _connect_channel(client: AsyncClient, admin_tok: str, oa: str, dept: str) -> None:
    # Kết nối kênh gắn sẵn phòng → hội thoại DANG_MO ngay, có department_id.
    r = await client.post(
        "/api/v1/channels",
        headers=_bearer(admin_tok),
        json={
            "platform": "ZALO",
            "external_channel_id": oa,
            "name": "OA",
            "credential": "tok",
            "department_id": dept,
        },
    )
    assert r.status_code == 201, r.text


async def _conv_moi_nhat(engine: AsyncEngine) -> str:
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT id FROM conversations ORDER BY created_at DESC LIMIT 1")
            )
        ).one()
    return str(row.id)


class TestRollupQuaWebhookVaBaoCao:
    async def test_inbound_reply_close_len_rollup_va_bao_cao(
        self, client_an: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        admin = await _login(client_an, "admin@x.vn")
        await _connect_channel(client_an, admin, "oa_an_1", ids["phong"])

        # 1) Khách nhắn → inbound rollup +1 (hook post_ingest).
        await _khach_nhan(client_an, "oa_an_1", "kh1", "m1")
        conv = await _conv_moi_nhat(engine)

        # 2) Kênh gắn sẵn phòng → hội thoại đã DANG_MO. Admin nhận rồi trả lời →
        # outbound rollup +1 (hook post_reply).
        r = await client_an.post(f"/api/v1/inbox/{conv}/take", headers=_bearer(admin))
        assert r.status_code == 200, r.text
        r = await client_an.post(
            f"/api/v1/inbox/{conv}/reply", headers=_bearer(admin), json={"text": "chao ban"}
        )
        assert r.status_code == 200, r.text

        # 3) Đóng → closed/handled rollup +1 (hook post_close).
        r = await client_an.post(f"/api/v1/inbox/{conv}/close", headers=_bearer(admin))
        assert r.status_code == 200, r.text

        # Báo cáo khối lượng: Admin thấy phòng KD có inbound + outbound + closed.
        r = await client_an.get(
            "/api/v1/analytics/conversations",
            headers=_bearer(admin),
            params={"from": HOM_NAY, "to": HOM_NAY, "department_id": ids["phong"]},
        )
        assert r.status_code == 200, r.text
        items = r.json()
        assert len(items) == 1
        assert items[0]["inbound_count"] == 1
        assert items[0]["outbound_count"] == 1
        assert items[0]["closed_count"] == 1

        # Báo cáo nhân viên: admin (người nhận) có handled 1.
        r = await client_an.get(
            "/api/v1/analytics/agents",
            headers=_bearer(admin),
            params={"from": HOM_NAY, "to": HOM_NAY},
        )
        assert r.status_code == 200
        rows = r.json()
        handled = {row["user_id"]: row["handled_count"] for row in rows}
        assert handled.get(ids["admin"]) == 1
        # Nhận việc thủ công (/take) KHÔNG phải auto-assign → không có dòng
        # assignment_log → assigned_count = 0 (chỉ auto-assign #3 mới ghi log).
        assigned = {row["user_id"]: row["assigned_count"] for row in rows}
        assert assigned.get(ids["admin"]) == 0

    async def test_staff_khong_xem_bao_cao(
        self, client_an: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _seed(engine)
        tok = await _login(client_an, "staff@x.vn")
        r = await client_an.get(
            "/api/v1/analytics/conversations",
            headers=_bearer(tok),
            params={"from": HOM_NAY, "to": HOM_NAY},
        )
        assert r.status_code == 403, r.text

    async def test_manager_ep_phong_minh(self, client_an: AsyncClient, engine: AsyncEngine) -> None:
        ids = await _seed(engine)
        admin = await _login(client_an, "admin@x.vn")
        await _connect_channel(client_an, admin, "oa_an_2", ids["phong2"])
        await _khach_nhan(client_an, "oa_an_2", "kh2", "m2")

        # Manager phòng KD (phong) xem, cố lọc phong2 → vẫn chỉ phòng mình (rỗng).
        tok_m = await _login(client_an, "manager@x.vn")
        r = await client_an.get(
            "/api/v1/analytics/conversations",
            headers=_bearer(tok_m),
            params={"from": HOM_NAY, "to": HOM_NAY, "department_id": ids["phong2"]},
        )
        assert r.status_code == 200
        # Dữ liệu thuộc phong2 nhưng Manager bị ép về phong → không thấy gì.
        assert all(item["department_id"] == ids["phong"] for item in r.json())


class TestOverviewBe8:
    async def test_tong_quan_qua_webhook_that(
        self, client_an: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        admin = await _login(client_an, "admin@x.vn")
        await _connect_channel(client_an, admin, "oa_ov_1", ids["phong"])
        await _connect_channel(client_an, admin, "oa_ov_2", ids["phong2"])

        # Phòng KD: 1 hội thoại được trả lời. Phòng 2: 1 hội thoại chưa ai trả lời.
        await _khach_nhan(client_an, "oa_ov_1", "kh1", "m1")
        conv = await _conv_moi_nhat(engine)
        await client_an.post(f"/api/v1/inbox/{conv}/take", headers=_bearer(admin))
        r = await client_an.post(
            f"/api/v1/inbox/{conv}/reply", headers=_bearer(admin), json={"text": "chao"}
        )
        assert r.status_code == 200, r.text
        await _khach_nhan(client_an, "oa_ov_2", "kh2", "m2")

        khoang = {"from": HOM_NAY, "to": HOM_NAY}
        r = await client_an.get("/api/v1/analytics/overview", headers=_bearer(admin), params=khoang)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["totals"]["inbound_count"] == 2
        assert body["totals"]["outbound_count"] == 1
        assert (body["conversations_with_inbound"], body["conversations_replied"]) == (2, 1)
        assert body["response_rate"] == 0.5
        assert body["first_response_samples"] == 1
        assert body["avg_first_response_seconds"] is not None
        assert [d["date"] for d in body["daily"]] == [HOM_NAY]

        # Manager phòng KD cố xem phòng 2 -> vẫn bị ép về phòng mình (RB-4).
        tok_m = await _login(client_an, "manager@x.vn")
        r = await client_an.get(
            "/api/v1/analytics/overview",
            headers=_bearer(tok_m),
            params={**khoang, "department_id": ids["phong2"]},
        )
        assert r.status_code == 200, r.text
        assert r.json()["response_rate"] == 1.0
        assert r.json()["totals"]["inbound_count"] == 1

        r = await client_an.get(
            "/api/v1/analytics/overview",
            headers=_bearer(await _login(client_an, "staff@x.vn")),
            params=khoang,
        )
        assert r.status_code == 403, r.text

    async def test_khoang_nguoc_bi_tu_choi(
        self, client_an: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _seed(engine)
        admin = await _login(client_an, "admin@x.vn")
        r = await client_an.get(
            "/api/v1/analytics/overview",
            headers=_bearer(admin),
            params={"from": "2026-09-10", "to": "2026-09-01"},
        )
        assert r.status_code == 400, r.text
        assert r.json()["error"]["code"] == "ANALYTICS_INVALID_DATE_RANGE"


class TestRebuildEndpoint:
    async def test_chi_admin_va_chan_range_dai(
        self, client_an: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _seed(engine)
        # Manager không được rebuild.
        tok_m = await _login(client_an, "manager@x.vn")
        r = await client_an.post(
            "/api/v1/analytics/rollups/rebuild",
            headers=_bearer(tok_m),
            params={"from": HOM_NAY, "to": HOM_NAY},
        )
        assert r.status_code == 403, r.text

        # Admin range hợp lệ (một ngày) OK.
        admin = await _login(client_an, "admin@x.vn")
        r = await client_an.post(
            "/api/v1/analytics/rollups/rebuild",
            headers=_bearer(admin),
            params={"from": HOM_NAY, "to": HOM_NAY},
        )
        assert r.status_code == 200, r.text
        assert r.json()["days_rebuilt"] == 1

        # Admin range quá dài → 400.
        r = await client_an.post(
            "/api/v1/analytics/rollups/rebuild",
            headers=_bearer(admin),
            params={"from": "2020-01-01", "to": "2026-12-31"},
        )
        assert r.status_code == 400, r.text
