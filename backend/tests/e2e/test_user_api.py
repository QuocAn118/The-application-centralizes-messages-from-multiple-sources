import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU = "MatKhauDung123"


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
            {"id": new_id(), "hash": BcryptPasswordHasher(rounds=4).hash(MAT_KHAU)},
        )


async def _token(client: AsyncClient, email: str, mat_khau: str = MAT_KHAU) -> str:
    phan_hoi = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": mat_khau}
    )
    assert phan_hoi.status_code == 200, phan_hoi.text
    return phan_hoi.json()["access_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestLuongThietLapBanDau:
    async def test_admin_tao_phong_ban_roi_tao_nhan_vien(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        """Luồng dựng hệ thống từ đầu — kịch bản quan trọng nhất của Foundation."""
        await _tao_admin(engine)
        token = await _token(client, "admin@congty.vn")

        phong = await client.post(
            "/api/v1/departments",
            json={"name": "Tư vấn sản phẩm A"},
            headers=_bearer(token),
        )
        assert phong.status_code == 201
        phong_id = phong.json()["id"]

        manager = await client.post(
            "/api/v1/users",
            json={
                "email": "quanly@congty.vn",
                "full_name": "Trần Quản Lý",
                "role": "MANAGER",
                "department_id": phong_id,
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )
        assert manager.status_code == 201

        staff = await client.post(
            "/api/v1/users",
            json={
                "email": "nhanvien@congty.vn",
                "full_name": "Lê Nhân Viên",
                "role": "STAFF",
                "department_id": phong_id,
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )
        assert staff.status_code == 201

    async def test_nhan_vien_moi_buoc_phai_doi_mat_khau(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(token)
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "moi@congty.vn",
                "full_name": "Nhân viên mới",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )

        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "moi@congty.vn", "password": "MatKhauTam123"},
        )

        assert dang_nhap.json()["must_change_password"] is True


class TestPhanQuyen:
    async def test_khong_tao_duoc_manager_thu_hai_trong_phong(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(token)
        )
        phong_id = phong.json()["id"]
        await client.post(
            "/api/v1/users",
            json={
                "email": "m0@congty.vn",
                "full_name": "Quản lý",
                "role": "MANAGER",
                "department_id": phong_id,
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )

        thu_hai = await client.post(
            "/api/v1/users",
            json={
                "email": "m2@congty.vn",
                "full_name": "Quản lý 2",
                "role": "MANAGER",
                "department_id": phong_id,
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )

        assert thu_hai.status_code == 422
        assert thu_hai.json()["error"]["code"] == "DEPARTMENT_ALREADY_HAS_MANAGER"

    async def test_staff_khong_goi_duoc_endpoint_quan_tri(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        admin_token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(admin_token)
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "staff@congty.vn",
                "full_name": "Nhân viên",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(admin_token),
        )
        staff_token = await _token(client, "staff@congty.vn", "MatKhauTam123")

        phan_hoi = await client.post(
            "/api/v1/users",
            json={
                "email": "khac@congty.vn",
                "full_name": "Người khác",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(staff_token),
        )

        assert phan_hoi.status_code == 403

    async def test_manager_chi_thay_nhan_vien_phong_minh(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        admin_token = await _token(client, "admin@congty.vn")
        phong_a = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(admin_token)
        )
        phong_b = await client.post(
            "/api/v1/departments", json={"name": "Phòng B"}, headers=_bearer(admin_token)
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "ma@congty.vn",
                "full_name": "Quản lý A",
                "role": "MANAGER",
                "department_id": phong_a.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(admin_token),
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "sb@congty.vn",
                "full_name": "Nhân viên B",
                "role": "STAFF",
                "department_id": phong_b.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(admin_token),
        )
        manager_token = await _token(client, "ma@congty.vn", "MatKhauTam123")

        danh_sach = await client.get(
            "/api/v1/users", headers=_bearer(manager_token)
        )

        emails = {u["email"] for u in danh_sach.json()["items"]}
        assert "sb@congty.vn" not in emails

    async def test_staff_khong_xem_duoc_nhat_ky(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        admin_token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(admin_token)
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "staff@congty.vn",
                "full_name": "Nhân viên",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(admin_token),
        )
        staff_token = await _token(client, "staff@congty.vn", "MatKhauTam123")

        phan_hoi = await client.get("/api/v1/audit-logs", headers=_bearer(staff_token))

        assert phan_hoi.status_code == 403


class TestVongDoiTaiKhoan:
    async def test_vo_hieu_hoa_thi_khong_dang_nhap_duoc(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        admin_token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(admin_token)
        )
        tao = await client.post(
            "/api/v1/users",
            json={
                "email": "nghi@congty.vn",
                "full_name": "Sắp nghỉ",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(admin_token),
        )
        user_id = tao.json()["id"]

        await client.post(
            f"/api/v1/users/{user_id}/deactivate", headers=_bearer(admin_token)
        )

        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "nghi@congty.vn", "password": "MatKhauTam123"},
        )
        assert dang_nhap.status_code == 400
        assert dang_nhap.json()["error"]["code"] == "INACTIVE_ACCOUNT"

    async def test_khong_vo_hieu_hoa_duoc_admin_cuoi_cung(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        token = await _token(client, "admin@congty.vn")
        toi = await client.get("/api/v1/auth/me", headers=_bearer(token))

        phan_hoi = await client.post(
            f"/api/v1/users/{toi.json()['id']}/deactivate", headers=_bearer(token)
        )

        assert phan_hoi.status_code == 422
        assert (
            phan_hoi.json()["error"]["code"] == "LAST_ADMIN_CANNOT_BE_DEACTIVATED"
        )

    async def test_khong_dong_duoc_phong_ban_con_nhan_vien(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(token)
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "con@congty.vn",
                "full_name": "Còn làm",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )

        phan_hoi = await client.post(
            f"/api/v1/departments/{phong.json()['id']}/deactivate",
            headers=_bearer(token),
        )

        assert phan_hoi.status_code == 422
        assert phan_hoi.json()["error"]["code"] == "DEPARTMENT_HAS_ACTIVE_MEMBERS"


class TestNhatKyGhiNhanDayDu:
    async def test_moi_thao_tac_deu_de_lai_ban_ghi(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        token = await _token(client, "admin@congty.vn")
        phong = await client.post(
            "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(token)
        )
        await client.post(
            "/api/v1/users",
            json={
                "email": "x@congty.vn",
                "full_name": "Người X",
                "role": "STAFF",
                "department_id": phong.json()["id"],
                "password": "MatKhauTam123",
            },
            headers=_bearer(token),
        )

        nhat_ky = await client.get("/api/v1/audit-logs", headers=_bearer(token))

        hanh_dong = {e["action"] for e in nhat_ky.json()["items"]}
        assert "department.created" in hanh_dong
        assert "user.created" in hanh_dong
        assert "auth.login_succeeded" in hanh_dong
