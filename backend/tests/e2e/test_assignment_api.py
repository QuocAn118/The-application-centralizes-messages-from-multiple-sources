"""E2E cho #3 Auto-Assignment: tự gán nhân viên + hàng đợi + kéo thủ công + đóng.

Đi qua HTTP thật (ASGI) + PostgreSQL thật. Classifier LLM của #2 được thay bằng
bản GIẢ tất định (bơm ``app.state.keyword_classifier_factory``) để chuỗi
webhook → #2 phân phòng → #3 tự gán chạy trọn mà không ra mạng.

"Đang trong ca" so theo giờ nghiệp vụ địa phương (``app_timezone``, mặc định
Asia/Ho_Chi_Minh) với ``clock.now()`` thực. Để tất định bất kể chạy lúc nào,
seed ca phủ **trọn ngày địa phương** (00:00-23:59:59) của hôm nay theo giờ VN.
"""

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

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
_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class _FakeClassifier:
    """Classifier tất định: luôn chọn ``department_id`` cấu hình + tin cậy cao."""

    def __init__(self, department_id: UUID) -> None:
        self._department_id = department_id

    async def classify(self, texts, departments):  # type: ignore[no-untyped-def]
        return ClassificationResult(
            department_id=self._department_id,
            confidence=Decimal("0.95"),
            terms=(ExtractedTerm(text="can tu van", normalized="can tu van"),),
        )


def _mock_adapter_client() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message_id": "x"}, content=b"anh")

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def app_as(app_test):  # type: ignore[no-untyped-def]
    """App e2e với adapter Zalo bí mật đã biết (client giả) + LLM giả về phòng KD."""
    app_test.state.inbox_adapter_registry = ChannelAdapterRegistry(
        [ZaloAdapter(ZALO_APP_ID, ZALO_OA_SECRET, client_factory=_mock_adapter_client)]
    )
    return app_test


@pytest.fixture
async def client_as(app_as):  # type: ignore[no-untyped-def]
    async with AsyncClient(transport=ASGITransport(app=app_as), base_url="http://test") as ac:
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


async def _seed_ca_ca_ngay(engine: AsyncEngine, user_id: str, department_id: str) -> None:
    """Seed một ShiftAssignment ACTIVE phủ trọn ngày địa phương hôm nay cho user.

    Phải seed Shift thật trước (FK shift_id → shifts.id). ``work_date`` là ngày
    **địa phương** (giờ VN) vì pool tính hôm nay sau khi quy đổi múi giờ.
    """
    from src.shared.domain.identifiers import new_id

    hom_nay_local = datetime.now(_TZ).date()
    shift_id = str(new_id())
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO shifts (id, department_id, name, start_time, end_time, "
                "is_active, created_at, updated_at) VALUES (:id, :dept, :ten, "
                "'00:00:00', '23:59:59', true, now(), now())"
            ),
            {"id": shift_id, "dept": department_id, "ten": "Ca ca ngay"},
        )
        await conn.execute(
            text(
                "INSERT INTO shift_assignments (id, shift_id, user_id, department_id, "
                "work_date, start_time, end_time, status, created_at, updated_at) VALUES "
                "(:id, :shift, :uid, :dept, :ngay, '00:00:00', '23:59:59', 'ACTIVE', "
                "now(), now())"
            ),
            {
                "id": str(new_id()),
                "shift": shift_id,
                "uid": user_id,
                "dept": department_id,
                "ngay": hom_nay_local,
            },
        )


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


async def _tao_tu_khoa(client: AsyncClient, department_id: str) -> None:
    r = await client.post(
        "/api/v1/keywords",
        headers=_bearer(await _login(client, "manager@x.vn")),
        json={"department_id": department_id, "text": "tu van"},
    )
    assert r.status_code == 201, r.text


async def _khach_nhan_tin(
    app_as, client: AsyncClient, dept_id: str, oa: str, sender: str, msg: str
) -> None:
    """Cấu hình LLM giả về phòng ``dept_id`` rồi bắn webhook một tin của khách."""
    app_as.state.keyword_classifier_factory = lambda: _FakeClassifier(UUID(dept_id))
    raw = _webhook_zalo(oa, sender, msg, "toi can tu van san pham")
    r = await client.post(
        "/api/v1/webhooks/ZALO", content=raw, headers={"X-ZEvent-Signature": _ky_zalo(raw)}
    )
    assert r.status_code == 200, r.text


async def _hoi_thoai_moi_nhat(engine: AsyncEngine):  # type: ignore[no-untyped-def]
    async with engine.begin() as conn:
        return (
            await conn.execute(
                text(
                    "SELECT id, status, department_id, assigned_user_id FROM conversations "
                    "ORDER BY created_at DESC LIMIT 1"
                )
            )
        ).one()


# ----- Trigger tự gán sau webhook (#2 phân phòng → #3 tự gán) -----


class TestTuGanQuaWebhook:
    async def test_khach_nhan_tin_thi_tu_gan_nhan_vien_trong_ca(
        self, app_as, client_as: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        await _seed_ca_ca_ngay(engine, ids["staff"], ids["phong"])  # staff trong ca
        admin = await _login(client_as, "admin@x.vn")
        await _connect_channel_no_dept(client_as, admin, "oa_as_1")
        await _tao_tu_khoa(client_as, ids["phong"])

        await _khach_nhan_tin(app_as, client_as, ids["phong"], "oa_as_1", "kh1", "m1")

        # #2 phân về phòng, #3 tự gán cho staff (người duy nhất trong ca).
        row = await _hoi_thoai_moi_nhat(engine)
        assert row.status == "DANG_MO"
        assert str(row.department_id) == ids["phong"]
        assert str(row.assigned_user_id) == ids["staff"]

    async def test_khong_ai_trong_ca_thi_vao_hang_doi(
        self, app_as, client_as: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        # KHÔNG seed ca cho ai → không ai trong ca.
        admin = await _login(client_as, "admin@x.vn")
        await _connect_channel_no_dept(client_as, admin, "oa_as_2")
        await _tao_tu_khoa(client_as, ids["phong"])

        await _khach_nhan_tin(app_as, client_as, ids["phong"], "oa_as_2", "kh2", "m2")

        # Phân được phòng nhưng không gán ai — nằm trong hàng đợi (assigned_user_id NULL).
        row = await _hoi_thoai_moi_nhat(engine)
        assert row.status == "DANG_MO"
        assert str(row.department_id) == ids["phong"]
        assert row.assigned_user_id is None


# ----- Endpoint kéo hàng đợi thủ công + phân quyền -----


class TestKeoHangDoiThuCong:
    async def test_manager_keo_hang_doi_phong_minh(
        self, app_as, client_as: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        admin = await _login(client_as, "admin@x.vn")
        await _connect_channel_no_dept(client_as, admin, "oa_as_3")
        await _tao_tu_khoa(client_as, ids["phong"])

        # Chưa ai trong ca lúc tin vào → hội thoại vào hàng đợi.
        await _khach_nhan_tin(app_as, client_as, ids["phong"], "oa_as_3", "kh3", "m3")
        row = await _hoi_thoai_moi_nhat(engine)
        assert row.assigned_user_id is None

        # Giờ cho staff vào ca rồi Manager kéo hàng đợi thủ công.
        await _seed_ca_ca_ngay(engine, ids["staff"], ids["phong"])
        tok_m = await _login(client_as, "manager@x.vn")
        r = await client_as.post(
            f"/api/v1/departments/{ids['phong']}/auto-assign", headers=_bearer(tok_m)
        )
        assert r.status_code == 200, r.text
        assert r.json()["assigned"] == 1

        row = await _hoi_thoai_moi_nhat(engine)
        assert str(row.assigned_user_id) == ids["staff"]

    async def test_staff_khong_keo_duoc(self, client_as: AsyncClient, engine: AsyncEngine) -> None:
        ids = await _seed(engine)
        tok = await _login(client_as, "staff@x.vn")
        r = await client_as.post(
            f"/api/v1/departments/{ids['phong']}/auto-assign", headers=_bearer(tok)
        )
        assert r.status_code == 403, r.text

    async def test_manager_khong_keo_phong_khac(
        self, client_as: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        tok = await _login(client_as, "manager2@x.vn")  # manager phòng khác
        r = await client_as.post(
            f"/api/v1/departments/{ids['phong']}/auto-assign", headers=_bearer(tok)
        )
        assert r.status_code == 403, r.text


# ----- Trigger kéo hàng đợi sau khi đóng hội thoại -----


class TestDongHoiThoaiKeoViecKe:
    async def test_dong_mot_viec_thi_keo_viec_dang_cho(
        self, app_as, client_as: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        # Chỉ staff trong ca; tải 1 hội thoại/lần để lần đầu chỉ gán 1.
        await _seed_ca_ca_ngay(engine, ids["staff"], ids["phong"])
        admin = await _login(client_as, "admin@x.vn")
        await _connect_channel_no_dept(client_as, admin, "oa_as_4")
        await _tao_tu_khoa(client_as, ids["phong"])

        # Hội thoại A: khách 1 nhắn → tự gán cho staff.
        await _khach_nhan_tin(app_as, client_as, ids["phong"], "oa_as_4", "khA", "mA")
        row_a = await _hoi_thoai_moi_nhat(engine)
        assert str(row_a.assigned_user_id) == ids["staff"]

        # Hội thoại B: khách 2 nhắn. Staff đã có tải 1; vẫn là người duy nhất trong
        # ca nên #3 vẫn gán B cho staff (cân bằng tải chỉ đổi khi có người khác).
        await _khach_nhan_tin(app_as, client_as, ids["phong"], "oa_as_4", "khB", "mB")
        row_b = await _hoi_thoai_moi_nhat(engine)
        conv_b = str(row_b.id)
        assert str(row_b.assigned_user_id) == ids["staff"]

        # Ép hội thoại B trở lại hàng đợi (gỡ người nhận) để mô phỏng việc còn chờ,
        # rồi đóng hội thoại A → hook post-close kéo B cho staff (vừa rảnh).
        async with engine.begin() as conn:
            await conn.execute(
                text("UPDATE conversations SET assigned_user_id = NULL WHERE id = :id"),
                {"id": conv_b},
            )

        tok_staff = await _login(client_as, "staff@x.vn")
        r = await client_as.post(f"/api/v1/inbox/{row_a.id}/close", headers=_bearer(tok_staff))
        assert r.status_code == 200, r.text

        # Hook post-close đã kéo B cho staff.
        async with engine.begin() as conn:
            row = (
                await conn.execute(
                    text("SELECT assigned_user_id, status FROM conversations WHERE id = :id"),
                    {"id": conv_b},
                )
            ).one()
        assert str(row.assigned_user_id) == ids["staff"]
        assert row.status == "DANG_MO"
