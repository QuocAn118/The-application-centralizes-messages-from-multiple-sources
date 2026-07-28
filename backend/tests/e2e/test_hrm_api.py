"""E2E cho luồng HRM: ca làm việc, KPI, đơn từ — qua HTTP thật + PostgreSQL thật.

Seed Admin/Manager/Staff qua identity, login lấy token, rồi đi các luồng chính
và kiểm phân quyền theo phòng ở tầng HTTP.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU = "MatKhau123ABC"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _seed(engine: AsyncEngine) -> dict[str, str]:
    """Tạo 1 phòng + admin + manager + staff. Trả về id các thực thể (str)."""
    from src.modules.identity.infrastructure.security.password_hasher import (
        BcryptPasswordHasher,
    )
    from src.shared.domain.identifiers import new_id

    h = BcryptPasswordHasher(rounds=4).hash(MAT_KHAU)
    ids = {
        "phong": str(new_id()),
        "admin": str(new_id()),
        "manager": str(new_id()),
        "staff": str(new_id()),
    }
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO departments (id, name, description, is_active, created_at, "
                "updated_at) VALUES (:id, 'Kinh doanh', NULL, true, now(), now())"
            ),
            {"id": ids["phong"]},
        )

        async def them_user(uid: str, email: str, role: str, dept: str | None) -> None:
            await conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, full_name, phone, role, "
                    "department_id, is_active, must_change_password, last_login_at, "
                    "created_at, updated_at) VALUES (:id, :email, :h, :name, NULL, :role, "
                    ":dept, true, false, NULL, now(), now())"
                ),
                {"id": uid, "email": email, "h": h, "name": role, "role": role, "dept": dept},
            )

        await them_user(ids["admin"], "admin@x.vn", "ADMIN", None)
        await them_user(ids["manager"], "manager@x.vn", "MANAGER", ids["phong"])
        await them_user(ids["staff"], "staff@x.vn", "STAFF", ids["phong"])
    return ids


async def _login(client: AsyncClient, email: str) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": MAT_KHAU})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


class TestShiftFlow:
    async def test_manager_tao_ca_va_phan_ca(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        tok_manager = await _login(client, "manager@x.vn")

        # Tạo ca cho phòng mình.
        r = await client.post(
            "/api/v1/shifts",
            headers=_bearer(tok_manager),
            json={
                "department_id": ids["phong"],
                "name": "Ca sáng",
                "start_time": "08:00:00",
                "end_time": "12:00:00",
            },
        )
        assert r.status_code == 201, r.text
        shift_id = r.json()["id"]

        # Phân ca cho staff.
        r = await client.post(
            "/api/v1/shift-assignments",
            headers=_bearer(tok_manager),
            json={"shift_id": shift_id, "user_id": ids["staff"], "work_date": "2099-08-05"},
        )
        assert r.status_code == 201, r.text
        assert r.json()["user_id"] == ids["staff"]

    async def test_chong_ca_tra_409(self, client: AsyncClient, engine: AsyncEngine) -> None:
        ids = await _seed(engine)
        tok = await _login(client, "manager@x.vn")

        async def tao_ca(start: str, end: str) -> str:
            r = await client.post(
                "/api/v1/shifts",
                headers=_bearer(tok),
                json={
                    "department_id": ids["phong"],
                    "name": "Ca",
                    "start_time": start,
                    "end_time": end,
                },
            )
            return r.json()["id"]

        ca1 = await tao_ca("08:00:00", "12:00:00")
        ca2 = await tao_ca("11:00:00", "15:00:00")
        await client.post(
            "/api/v1/shift-assignments",
            headers=_bearer(tok),
            json={"shift_id": ca1, "user_id": ids["staff"], "work_date": "2099-08-05"},
        )
        r = await client.post(
            "/api/v1/shift-assignments",
            headers=_bearer(tok),
            json={"shift_id": ca2, "user_id": ids["staff"], "work_date": "2099-08-05"},
        )
        assert r.status_code == 409, r.text

    async def test_staff_khong_tao_ca_duoc(self, client: AsyncClient, engine: AsyncEngine) -> None:
        ids = await _seed(engine)
        tok_staff = await _login(client, "staff@x.vn")

        r = await client.post(
            "/api/v1/shifts",
            headers=_bearer(tok_staff),
            json={
                "department_id": ids["phong"],
                "name": "Ca",
                "start_time": "08:00:00",
                "end_time": "12:00:00",
            },
        )
        assert r.status_code == 403, r.text


class TestKpiFlow:
    async def test_dat_muc_tieu_va_xem_tien_do(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        ids = await _seed(engine)
        tok = await _login(client, "manager@x.vn")

        r = await client.post(
            "/api/v1/kpi-targets",
            headers=_bearer(tok),
            json={
                "subject_type": "USER",
                "subject_id": ids["staff"],
                "metric_type": "CONVERSATIONS_CLOSED",
                "period_year": 2099,
                "period_month": 8,
                "target_value": "200",
            },
        )
        assert r.status_code == 201, r.text

        # Xem tiến độ: chưa có hội thoại nào -> actual 0, percent 0.
        r = await client.get(
            "/api/v1/kpi-progress",
            headers=_bearer(tok),
            params={
                "subject_type": "USER",
                "subject_id": ids["staff"],
                "metric_type": "CONVERSATIONS_CLOSED",
                "period_year": 2099,
                "period_month": 8,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["target_value"] == "200.00"
        assert body["actual_value"] == "0"


class TestRequestFlow:
    async def test_staff_gui_manager_duyet(self, client: AsyncClient, engine: AsyncEngine) -> None:
        ids = await _seed(engine)
        tok_staff = await _login(client, "staff@x.vn")
        tok_manager = await _login(client, "manager@x.vn")

        # Staff gửi đơn nghỉ phép.
        r = await client.post(
            "/api/v1/requests",
            headers=_bearer(tok_staff),
            json={
                "request_type": "NGHI_PHEP",
                "reason": "Việc gia đình",
                "leave_start": "2099-08-10",
                "leave_end": "2099-08-12",
            },
        )
        assert r.status_code == 201, r.text
        don_id = r.json()["id"]
        assert r.json()["status"] == "CHO_DUYET"

        # Manager duyệt.
        r = await client.post(f"/api/v1/requests/{don_id}/approve", headers=_bearer(tok_manager))
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "DA_DUYET"
        assert r.json()["decided_by"] == ids["manager"]

    async def test_staff_khong_duyet_don(self, client: AsyncClient, engine: AsyncEngine) -> None:
        await _seed(engine)
        tok_staff = await _login(client, "staff@x.vn")

        r = await client.post(
            "/api/v1/requests",
            headers=_bearer(tok_staff),
            json={"request_type": "TANG_LUONG", "reason": "x"},
        )
        don_id = r.json()["id"]

        # Staff khác không duyệt được (Staff không có quyền duyệt).
        r = await client.post(f"/api/v1/requests/{don_id}/approve", headers=_bearer(tok_staff))
        # Tự duyệt đơn mình -> 403.
        assert r.status_code == 403, r.text

    async def test_tu_choi_kem_ly_do(self, client: AsyncClient, engine: AsyncEngine) -> None:
        await _seed(engine)
        tok_staff = await _login(client, "staff@x.vn")
        tok_manager = await _login(client, "manager@x.vn")

        r = await client.post(
            "/api/v1/requests",
            headers=_bearer(tok_staff),
            json={"request_type": "TANG_LUONG", "reason": "Xin tăng lương"},
        )
        don_id = r.json()["id"]

        r = await client.post(
            f"/api/v1/requests/{don_id}/reject",
            headers=_bearer(tok_manager),
            json={"reason": "Chưa đủ điều kiện"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "TU_CHOI"
        assert r.json()["decision_reason"] == "Chưa đủ điều kiện"
