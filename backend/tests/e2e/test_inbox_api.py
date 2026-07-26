"""E2E cho luồng inbox đa kênh: webhook → inbox → phân → trả lời.

Đi qua HTTP thật (ASGI) + PostgreSQL thật để bắt lỗi tích hợp giữa router, use
case, adapter, repository mà test đơn lẻ không thấy.
"""

import hashlib
import json

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.modules.inbox.domain.value_objects.platform import Platform
from src.modules.inbox.infrastructure.channels.meta_adapter import MetaAdapter
from src.modules.inbox.infrastructure.channels.registry import ChannelAdapterRegistry
from src.modules.inbox.infrastructure.channels.zalo_adapter import ZaloAdapter

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU_ADMIN = "MatKhauAdmin123"
ZALO_APP_ID = "app_test"
ZALO_OA_SECRET = "oa_secret_test"
META_APP_SECRET = "meta_secret_test"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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
                "'Quản trị viên', NULL, 'ADMIN', NULL, true, false, NULL, now(), now())"
            ),
            {"id": new_id(), "hash": BcryptPasswordHasher(rounds=4).hash(MAT_KHAU_ADMIN)},
        )


def _mock_client() -> httpx.AsyncClient:
    """Client giả cho adapter: send trả message_id, download trả bytes — không ra mạng."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200, json={"data": {"message_id": "sent_1"}, "message_id": "sent_1"}
            )
        return httpx.Response(200, content=b"anh-gia-lap")

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def app_inbox(app_test):  # type: ignore[no-untyped-def]
    """App e2e với adapter dùng bí mật đã biết + client giả (không ra mạng)."""
    app_test.state.inbox_adapter_registry = ChannelAdapterRegistry(
        [
            ZaloAdapter(ZALO_APP_ID, ZALO_OA_SECRET, client_factory=_mock_client),
            MetaAdapter(Platform.FACEBOOK, META_APP_SECRET, client_factory=_mock_client),
            MetaAdapter(Platform.INSTAGRAM, META_APP_SECRET, client_factory=_mock_client),
        ]
    )
    return app_test


@pytest.fixture
async def client_inbox(app_inbox):  # type: ignore[no-untyped-def]
    async with AsyncClient(transport=ASGITransport(app=app_inbox), base_url="http://test") as ac:
        yield ac


def _ky_zalo(raw: bytes) -> str:
    ts = str(json.loads(raw)["timestamp"])
    chuoi = ZALO_APP_ID.encode() + raw + ts.encode() + ZALO_OA_SECRET.encode()
    return "mac=" + hashlib.sha256(chuoi).hexdigest()


def _webhook_zalo(oa_id: str, sender: str, msg_id: str, text_: str) -> bytes:
    return json.dumps(
        {
            "app_id": ZALO_APP_ID,
            "oa_id": oa_id,
            "timestamp": "1690000000000",
            "event_name": "user_send_text",
            "sender": {"id": sender},
            "message": {"msg_id": msg_id, "text": text_},
        }
    ).encode()


async def _dang_nhap_admin(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@congty.vn", "password": MAT_KHAU_ADMIN},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


async def test_luong_zalo_day_du(client_inbox: AsyncClient, engine: AsyncEngine) -> None:
    await _tao_admin(engine)
    admin = await _dang_nhap_admin(client_inbox)

    # 1. Admin tạo phòng + kênh Zalo gắn phòng đó.
    phong = await client_inbox.post(
        "/api/v1/departments",
        json={"name": "CSKH", "description": None},
        headers=_bearer(admin),
    )
    phong_id = phong.json()["id"]

    kenh = await client_inbox.post(
        "/api/v1/channels",
        json={
            "platform": "ZALO",
            "external_channel_id": "oa_100",
            "name": "OA CSKH",
            "credential": "zalo-oa-token-that",
            "department_id": phong_id,
        },
        headers=_bearer(admin),
    )
    assert kenh.status_code == 201
    # Credential KHÔNG lộ ra response.
    assert "credential" not in kenh.json()
    assert "zalo-oa-token-that" not in kenh.text

    # 2. Webhook Zalo gửi tin đến (ký đúng) → 200.
    raw = _webhook_zalo("oa_100", "khach_1", "msg_1", "Xin chào shop")
    wh = await client_inbox.post(
        "/api/v1/webhooks/ZALO",
        content=raw,
        headers={"X-ZEvent-Signature": _ky_zalo(raw)},
    )
    assert wh.status_code == 200

    # 3. Tin xuất hiện trong inbox, đúng phòng, trạng thái DANG_MO.
    inbox = await client_inbox.get("/api/v1/inbox", headers=_bearer(admin))
    assert inbox.status_code == 200
    items = inbox.json()["items"]
    assert len(items) == 1
    conv_id = items[0]["conversation_id"]
    assert items[0]["status"] == "DANG_MO"
    assert items[0]["department_id"] == phong_id

    # 4. Xem chi tiết: có tin đến.
    chi_tiet = await client_inbox.get(f"/api/v1/inbox/{conv_id}", headers=_bearer(admin))
    assert chi_tiet.json()["messages"][0]["text"] == "Xin chào shop"

    # 5. Admin trả lời → tin outbound được lưu.
    tra_loi = await client_inbox.post(
        f"/api/v1/inbox/{conv_id}/reply",
        json={"text": "Chào bạn, shop nghe ạ"},
        headers=_bearer(admin),
    )
    assert tra_loi.status_code == 200
    assert tra_loi.json()["direction"] == "OUTBOUND"

    # 6. Đóng hội thoại.
    dong = await client_inbox.post(f"/api/v1/inbox/{conv_id}/close", headers=_bearer(admin))
    assert dong.json()["status"] == "DA_DONG"


async def test_webhook_chu_ky_sai_tra_403(client_inbox: AsyncClient, engine: AsyncEngine) -> None:
    await _tao_admin(engine)
    admin = await _dang_nhap_admin(client_inbox)
    await client_inbox.post(
        "/api/v1/channels",
        json={
            "platform": "ZALO",
            "external_channel_id": "oa_200",
            "name": "OA",
            "credential": "t",
        },
        headers=_bearer(admin),
    )

    raw = _webhook_zalo("oa_200", "k1", "m1", "hi")
    wh = await client_inbox.post(
        "/api/v1/webhooks/ZALO",
        content=raw,
        headers={"X-ZEvent-Signature": "mac=deadbeef"},
    )
    assert wh.status_code == 403


async def test_webhook_trung_khong_nhan_doi(client_inbox: AsyncClient, engine: AsyncEngine) -> None:
    await _tao_admin(engine)
    admin = await _dang_nhap_admin(client_inbox)
    await client_inbox.post(
        "/api/v1/channels",
        json={
            "platform": "ZALO",
            "external_channel_id": "oa_300",
            "name": "OA",
            "credential": "t",
        },
        headers=_bearer(admin),
    )

    raw = _webhook_zalo("oa_300", "k1", "dup_msg", "hi")
    sig = {"X-ZEvent-Signature": _ky_zalo(raw)}
    r1 = await client_inbox.post("/api/v1/webhooks/ZALO", content=raw, headers=sig)
    r2 = await client_inbox.post("/api/v1/webhooks/ZALO", content=raw, headers=sig)
    assert r1.status_code == 200
    assert r2.status_code == 200  # vẫn 200 dù trùng

    inbox = await client_inbox.get("/api/v1/inbox", headers=_bearer(admin))
    conv_id = inbox.json()["items"][0]["conversation_id"]
    chi_tiet = await client_inbox.get(f"/api/v1/inbox/{conv_id}", headers=_bearer(admin))
    # Chỉ một tin, không nhân đôi.
    assert len(chi_tiet.json()["messages"]) == 1


async def test_kenh_chua_gan_phong_thi_cho_phan(
    client_inbox: AsyncClient, engine: AsyncEngine
) -> None:
    await _tao_admin(engine)
    admin = await _dang_nhap_admin(client_inbox)
    await client_inbox.post(
        "/api/v1/channels",
        json={
            "platform": "ZALO",
            "external_channel_id": "oa_400",
            "name": "OA",
            "credential": "t",
        },
        headers=_bearer(admin),
    )

    raw = _webhook_zalo("oa_400", "k1", "m1", "hi")
    await client_inbox.post(
        "/api/v1/webhooks/ZALO", content=raw, headers={"X-ZEvent-Signature": _ky_zalo(raw)}
    )

    inbox = await client_inbox.get("/api/v1/inbox", headers=_bearer(admin))
    item = inbox.json()["items"][0]
    assert item["status"] == "CHO_PHAN"
    assert item["department_id"] is None


async def _tao_nhan_vien(
    client: AsyncClient, admin: str, email: str, role: str, phong_id: str | None
) -> str:
    """Tạo user + đổi mật khẩu tạm + đăng nhập, trả access token của họ."""
    tao = await client.post(
        "/api/v1/users",
        json={
            "email": email,
            "full_name": "NV",
            "role": role,
            "department_id": phong_id,
            "password": "MatKhauTam123",
        },
        headers=_bearer(admin),
    )
    assert tao.status_code == 201, tao.text
    dn = await client.post("/api/v1/auth/login", json={"email": email, "password": "MatKhauTam123"})
    token = dn.json()["access_token"]
    await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "MatKhauTam123", "new_password": "MatKhauMoi123"},
        headers=_bearer(token),
    )
    dn2 = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "MatKhauMoi123"}
    )
    return dn2.json()["access_token"]


async def test_manager_phan_hoi_thoai_cho_phan(
    client_inbox: AsyncClient, engine: AsyncEngine
) -> None:
    await _tao_admin(engine)
    admin = await _dang_nhap_admin(client_inbox)
    phong = await client_inbox.post(
        "/api/v1/departments",
        json={"name": "Phong M", "description": None},
        headers=_bearer(admin),
    )
    phong_id = phong.json()["id"]
    manager = await _tao_nhan_vien(client_inbox, admin, "manager@congty.vn", "MANAGER", phong_id)

    # Kênh không gắn phòng -> tin vào CHO_PHAN.
    await client_inbox.post(
        "/api/v1/channels",
        json={
            "platform": "ZALO",
            "external_channel_id": "oa_500",
            "name": "OA",
            "credential": "t",
        },
        headers=_bearer(admin),
    )
    raw = _webhook_zalo("oa_500", "k1", "m1", "can tu van")
    await client_inbox.post(
        "/api/v1/webhooks/ZALO", content=raw, headers={"X-ZEvent-Signature": _ky_zalo(raw)}
    )

    # Manager thấy mục chờ-phân và phân được về phòng mình.
    inbox = await client_inbox.get("/api/v1/inbox", headers=_bearer(manager))
    conv_id = inbox.json()["items"][0]["conversation_id"]

    phan = await client_inbox.post(
        f"/api/v1/inbox/{conv_id}/assign",
        json={"department_id": phong_id},
        headers=_bearer(manager),
    )
    assert phan.status_code == 200
    assert phan.json()["status"] == "DANG_MO"
    assert phan.json()["department_id"] == phong_id


async def test_staff_khong_thay_hoi_thoai_phong_khac(
    client_inbox: AsyncClient, engine: AsyncEngine
) -> None:
    await _tao_admin(engine)
    admin = await _dang_nhap_admin(client_inbox)
    phong_a = (
        await client_inbox.post(
            "/api/v1/departments",
            json={"name": "Phong A", "description": None},
            headers=_bearer(admin),
        )
    ).json()["id"]
    phong_b = (
        await client_inbox.post(
            "/api/v1/departments",
            json={"name": "Phong B", "description": None},
            headers=_bearer(admin),
        )
    ).json()["id"]
    staff_b = await _tao_nhan_vien(client_inbox, admin, "staff_b@congty.vn", "STAFF", phong_b)

    # Kênh gắn phòng A -> hội thoại thuộc phòng A.
    await client_inbox.post(
        "/api/v1/channels",
        json={
            "platform": "ZALO",
            "external_channel_id": "oa_600",
            "name": "OA",
            "credential": "t",
            "department_id": phong_a,
        },
        headers=_bearer(admin),
    )
    raw = _webhook_zalo("oa_600", "k1", "m1", "hi")
    await client_inbox.post(
        "/api/v1/webhooks/ZALO", content=raw, headers={"X-ZEvent-Signature": _ky_zalo(raw)}
    )

    # Staff phòng B không thấy hội thoại phòng A.
    inbox = await client_inbox.get("/api/v1/inbox", headers=_bearer(staff_b))
    assert inbox.json()["items"] == []


async def test_staff_khong_tao_duoc_kenh(client_inbox: AsyncClient, engine: AsyncEngine) -> None:
    await _tao_admin(engine)
    admin = await _dang_nhap_admin(client_inbox)
    phong = (
        await client_inbox.post(
            "/api/v1/departments",
            json={"name": "P", "description": None},
            headers=_bearer(admin),
        )
    ).json()["id"]
    staff = await _tao_nhan_vien(client_inbox, admin, "staff@congty.vn", "STAFF", phong)

    r = await client_inbox.post(
        "/api/v1/channels",
        json={
            "platform": "ZALO",
            "external_channel_id": "oa_700",
            "name": "OA",
            "credential": "t",
        },
        headers=_bearer(staff),
    )
    assert r.status_code == 403
