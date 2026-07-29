"""E2E cho #2 Keyword & AI: CRUD từ khoá + phân tích + tự phân qua webhook.

Đi qua HTTP thật (ASGI) + PostgreSQL thật. Classifier LLM được thay bằng bản GIẢ
tất định (bơm vào ``app.state.keyword_classifier_factory``) để không ra mạng; phần
Claude thật để test thủ công ngoài CI.
"""

import hashlib
import json
from decimal import Decimal
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.modules.inbox.infrastructure.channels.registry import ChannelAdapterRegistry
from src.modules.inbox.infrastructure.channels.zalo_adapter import ZaloAdapter
from src.modules.keyword.domain.value_objects.extracted_term import (
    ClassificationResult,
    ExtractedTerm,
)

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU = "MatKhau123ABC"
ZALO_APP_ID = "app_test"
ZALO_OA_SECRET = "oa_secret_test"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class _FakeClassifier:
    """Classifier tất định: chọn ``department_id`` cố định + tin cậy cấu hình.

    ``raise_error=True`` mô phỏng LLM hỏng (→ NOT_ANALYZED, tin vẫn nguyên).
    """

    def __init__(
        self,
        department_id: UUID | None,
        confidence: Decimal,
        raise_error: bool = False,
    ) -> None:
        self._department_id = department_id
        self._confidence = confidence
        self._raise_error = raise_error

    async def classify(self, texts, departments):  # type: ignore[no-untyped-def]
        from src.modules.keyword.domain.ports import ClassifierError

        if self._raise_error:
            raise ClassifierError("LLM giả lỗi")
        return ClassificationResult(
            department_id=self._department_id,
            confidence=self._confidence,
            terms=(ExtractedTerm(text="can tu van", normalized="can tu van"),),
        )


def _mock_adapter_client() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message_id": "x"}, content=b"anh")

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def app_kw(app_test):  # type: ignore[no-untyped-def]
    """App e2e với adapter Zalo bí mật đã biết (client giả, không ra mạng)."""
    app_test.state.inbox_adapter_registry = ChannelAdapterRegistry(
        [ZaloAdapter(ZALO_APP_ID, ZALO_OA_SECRET, client_factory=_mock_adapter_client)]
    )
    return app_test


@pytest.fixture
async def client_kw(app_kw):  # type: ignore[no-untyped-def]
    async with AsyncClient(transport=ASGITransport(app=app_kw), base_url="http://test") as ac:
        yield ac


async def _seed(engine: AsyncEngine) -> dict[str, str]:
    """1 phòng + admin + manager(phòng) + staff(phòng) + manager phòng khác."""
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
        for key, ten in (("phong", "Kinh doanh"), ("phong2", "Ky thuat")):
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


async def _connect_channel_no_dept(client: AsyncClient, admin_tok: str, oa_id: str) -> None:
    """Kết nối kênh Zalo KHÔNG gắn phòng → hội thoại rơi vào CHO_PHAN."""
    r = await client.post(
        "/api/v1/channels",
        headers=_bearer(admin_tok),
        json={
            "platform": "ZALO",
            "external_channel_id": oa_id,
            "name": "OA test",
            "credential": "zalo-token",
        },
    )
    assert r.status_code == 201, r.text


# ----- CRUD từ khoá -----


class TestKeywordCrud:
    async def test_manager_crud_tu_khoa_phong_minh(
        self, client_kw: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        tok = await _login(client_kw, "manager@x.vn")

        r = await client_kw.post(
            "/api/v1/keywords",
            headers=_bearer(tok),
            json={"department_id": ids["phong"], "text": "Bảo Hành"},
        )
        assert r.status_code == 201, r.text
        kw_id = r.json()["id"]
        assert r.json()["normalized"] == "bao hanh"

        r = await client_kw.get("/api/v1/keywords", headers=_bearer(tok))
        assert r.status_code == 200
        assert [k["id"] for k in r.json()] == [kw_id]

        r = await client_kw.patch(
            f"/api/v1/keywords/{kw_id}", headers=_bearer(tok), json={"text": "Khuyến Mãi"}
        )
        assert r.status_code == 200
        assert r.json()["normalized"] == "khuyen mai"

        r = await client_kw.delete(f"/api/v1/keywords/{kw_id}", headers=_bearer(tok))
        assert r.status_code == 204

    async def test_staff_khong_crud_duoc(self, client_kw: AsyncClient, engine: AsyncEngine) -> None:
        ids = await _seed(engine)
        tok = await _login(client_kw, "staff@x.vn")
        r = await client_kw.post(
            "/api/v1/keywords",
            headers=_bearer(tok),
            json={"department_id": ids["phong"], "text": "abc"},
        )
        assert r.status_code == 403, r.text

    async def test_manager_khong_tao_tu_khoa_phong_khac(
        self, client_kw: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        tok = await _login(client_kw, "manager@x.vn")
        r = await client_kw.post(
            "/api/v1/keywords",
            headers=_bearer(tok),
            json={"department_id": ids["phong2"], "text": "abc"},
        )
        assert r.status_code == 403, r.text


# ----- Tự phân qua webhook (hook post-ingest) -----


class TestAutoAssignViaWebhook:
    async def test_khach_nhan_tin_thi_tu_phan_ve_phong(
        self, app_kw, client_kw: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        admin = await _login(client_kw, "admin@x.vn")
        await _connect_channel_no_dept(client_kw, admin, "oa_kw_1")

        # Manager tạo từ khoá cho phòng mình.
        await client_kw.post(
            "/api/v1/keywords",
            headers=_bearer(await _login(client_kw, "manager@x.vn")),
            json={"department_id": ids["phong"], "text": "tu van"},
        )

        # LLM giả chọn đúng phòng, đủ tin cậy.
        app_kw.state.keyword_classifier_factory = lambda: _FakeClassifier(
            UUID(ids["phong"]), Decimal("0.9")
        )

        raw = _webhook_zalo("oa_kw_1", "khach_1", "m1", "toi can tu van san pham")
        r = await client_kw.post(
            "/api/v1/webhooks/ZALO", content=raw, headers={"X-ZEvent-Signature": _ky_zalo(raw)}
        )
        assert r.status_code == 200, r.text

        # Hội thoại giờ đã được tự phân về phòng (DANG_MO + department_id).
        async with engine.begin() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT status, department_id FROM conversations "
                        "ORDER BY created_at DESC LIMIT 1"
                    )
                )
            ).one()
        assert row.status == "DANG_MO"
        assert str(row.department_id) == ids["phong"]

        # Có bản ghi phân tích AUTO_ASSIGNED; Manager phòng xem được.
        tok_m = await _login(client_kw, "manager@x.vn")
        r = await client_kw.get("/api/v1/analyses", headers=_bearer(tok_m))
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["outcome"] == "AUTO_ASSIGNED"
        assert items[0]["suggested_department_id"] == ids["phong"]

    async def test_llm_loi_thi_tin_van_vao_va_giu_cho_phan(
        self, app_kw, client_kw: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _seed(engine)
        admin = await _login(client_kw, "admin@x.vn")
        await _connect_channel_no_dept(client_kw, admin, "oa_kw_2")

        # LLM giả LỖI.
        app_kw.state.keyword_classifier_factory = lambda: _FakeClassifier(
            None, Decimal("0"), raise_error=True
        )

        raw = _webhook_zalo("oa_kw_2", "khach_2", "m2", "hello shop")
        r = await client_kw.post(
            "/api/v1/webhooks/ZALO", content=raw, headers={"X-ZEvent-Signature": _ky_zalo(raw)}
        )
        # Tin vẫn nhận (200), hội thoại giữ CHO_PHAN.
        assert r.status_code == 200, r.text
        async with engine.begin() as conn:
            row = (
                await conn.execute(
                    text("SELECT status FROM conversations ORDER BY created_at DESC LIMIT 1")
                )
            ).one()
            so_tin = (await conn.execute(text("SELECT count(*) AS n FROM messages"))).one()
        assert row.status == "CHO_PHAN"
        assert so_tin.n == 1  # tin khách vẫn được lưu


# ----- Kích hoạt phân tích lại (force) -----


class TestRetriggerAnalysis:
    async def test_manager_kich_hoat_phan_tich_lai(
        self, app_kw, client_kw: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        admin = await _login(client_kw, "admin@x.vn")
        await _connect_channel_no_dept(client_kw, admin, "oa_kw_3")

        # LLM giả LỖI lúc tin đầu vào → hội thoại giữ CHO_PHAN, có bản ghi NOT_ANALYZED.
        app_kw.state.keyword_classifier_factory = lambda: _FakeClassifier(
            None, Decimal("0"), raise_error=True
        )
        raw = _webhook_zalo("oa_kw_3", "khach_3", "m3", "toi can tu van")
        await client_kw.post(
            "/api/v1/webhooks/ZALO", content=raw, headers={"X-ZEvent-Signature": _ky_zalo(raw)}
        )
        async with engine.begin() as conn:
            conv_id = (
                (
                    await conn.execute(
                        text("SELECT id FROM conversations ORDER BY created_at DESC LIMIT 1")
                    )
                )
                .one()
                .id
            )

        # Giờ LLM giả OK + có từ khoá → kích hoạt lại phải tự phân.
        await client_kw.post(
            "/api/v1/keywords",
            headers=_bearer(await _login(client_kw, "manager@x.vn")),
            json={"department_id": ids["phong"], "text": "tu van"},
        )
        app_kw.state.keyword_classifier_factory = lambda: _FakeClassifier(
            UUID(ids["phong"]), Decimal("0.95")
        )

        tok_m = await _login(client_kw, "manager@x.vn")
        r = await client_kw.post(
            f"/api/v1/conversations/{conv_id}/analyses", headers=_bearer(tok_m)
        )
        assert r.status_code == 200, r.text
        assert r.json()["outcome"] == "AUTO_ASSIGNED"

        async with engine.begin() as conn:
            row = (
                await conn.execute(
                    text("SELECT status, department_id FROM conversations WHERE id = :id"),
                    {"id": str(conv_id)},
                )
            ).one()
        assert row.status == "DANG_MO"
        assert str(row.department_id) == ids["phong"]

    async def test_staff_khong_kich_hoat_duoc(
        self, client_kw: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _seed(engine)
        tok = await _login(client_kw, "staff@x.vn")
        from src.shared.domain.identifiers import new_id

        r = await client_kw.post(f"/api/v1/conversations/{new_id()}/analyses", headers=_bearer(tok))
        assert r.status_code == 403, r.text
