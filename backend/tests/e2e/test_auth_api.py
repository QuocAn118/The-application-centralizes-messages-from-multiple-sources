import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU = "MatKhauDung123"


async def _tao_admin(engine: AsyncEngine, email: str = "admin@congty.vn") -> None:
    """Tạo sẵn một quản trị viên bằng câu lệnh trực tiếp."""
    from src.modules.identity.infrastructure.security.password_hasher import (
        BcryptPasswordHasher,
    )
    from src.shared.domain.identifiers import new_id

    chuoi_hash = BcryptPasswordHasher(rounds=4).hash(MAT_KHAU)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, full_name, phone, role, "
                "department_id, is_active, must_change_password, last_login_at, "
                "created_at, updated_at) VALUES (:id, :email, :hash, 'Quản trị viên', "
                "NULL, 'ADMIN', NULL, true, false, NULL, now(), now())"
            ),
            {"id": new_id(), "email": email, "hash": chuoi_hash},
        )


class TestDangNhap:
    async def test_dang_nhap_thanh_cong(self, client: AsyncClient, engine: AsyncEngine) -> None:
        await _tao_admin(engine)

        phan_hoi = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )

        assert phan_hoi.status_code == 200
        noi_dung = phan_hoi.json()
        assert noi_dung["access_token"]
        assert noi_dung["refresh_token"]
        assert noi_dung["token_type"] == "bearer"
        assert noi_dung["expires_in"] == 15 * 60

    async def test_mat_khau_sai_tra_ve_400(self, client: AsyncClient, engine: AsyncEngine) -> None:
        await _tao_admin(engine)

        phan_hoi = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": "SaiRoi123"},
        )

        assert phan_hoi.status_code == 400
        assert phan_hoi.json()["error"]["code"] == "INVALID_CREDENTIALS"

    async def test_email_khong_ton_tai_cho_cung_ma_loi(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        """Không được để lộ email nào có trong hệ thống."""
        await _tao_admin(engine)

        phan_hoi = await client.post(
            "/api/v1/auth/login",
            json={"email": "khongton@tai.vn", "password": MAT_KHAU},
        )

        assert phan_hoi.status_code == 400
        assert phan_hoi.json()["error"]["code"] == "INVALID_CREDENTIALS"

    async def test_email_sai_dinh_dang_tra_ve_422(self, client: AsyncClient) -> None:
        phan_hoi = await client.post(
            "/api/v1/auth/login",
            json={"email": "khong-phai-email", "password": MAT_KHAU},
        )

        assert phan_hoi.status_code == 422

    async def test_phan_hoi_khong_chua_hash_mat_khau(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)

        phan_hoi = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )

        assert "password_hash" not in phan_hoi.text
        assert "$2b$" not in phan_hoi.text


class TestThongTinCuaToi:
    async def test_lay_duoc_ho_so_khi_co_token(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        token = dang_nhap.json()["access_token"]

        phan_hoi = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert phan_hoi.status_code == 200
        assert phan_hoi.json()["email"] == "admin@congty.vn"
        assert phan_hoi.json()["role"] == "ADMIN"

    async def test_khong_tra_ve_hash_mat_khau(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        token = dang_nhap.json()["access_token"]

        phan_hoi = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert "password_hash" not in phan_hoi.json()


class TestLamMoiToken:
    async def test_lam_moi_tra_ve_cap_token_moi(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        cu = dang_nhap.json()["refresh_token"]

        phan_hoi = await client.post("/api/v1/auth/refresh", json={"refresh_token": cu})

        assert phan_hoi.status_code == 200
        assert phan_hoi.json()["refresh_token"] != cu

    async def test_dung_lai_token_cu_bi_tu_choi(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        cu = dang_nhap.json()["refresh_token"]
        await client.post("/api/v1/auth/refresh", json={"refresh_token": cu})

        phan_hoi = await client.post("/api/v1/auth/refresh", json={"refresh_token": cu})

        assert phan_hoi.status_code == 401

    async def test_tai_su_dung_thu_hoi_ca_chuoi(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        """Token bị tái sử dụng nghĩa là đã lộ — cả chuỗi mất hiệu lực."""
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        cu = dang_nhap.json()["refresh_token"]
        lam_moi = await client.post("/api/v1/auth/refresh", json={"refresh_token": cu})
        moi = lam_moi.json()["refresh_token"]

        await client.post("/api/v1/auth/refresh", json={"refresh_token": cu})

        phan_hoi = await client.post("/api/v1/auth/refresh", json={"refresh_token": moi})
        assert phan_hoi.status_code == 401


class TestDangXuat:
    async def test_dang_xuat_thu_hoi_token(self, client: AsyncClient, engine: AsyncEngine) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        access = dang_nhap.json()["access_token"]
        refresh = dang_nhap.json()["refresh_token"]

        phan_hoi = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh},
            headers={"Authorization": f"Bearer {access}"},
        )

        assert phan_hoi.status_code == 204
        lam_moi = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert lam_moi.status_code == 401


class TestDoiMatKhau:
    async def test_doi_mat_khau_thanh_cong(self, client: AsyncClient, engine: AsyncEngine) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        access = dang_nhap.json()["access_token"]

        phan_hoi = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": MAT_KHAU, "new_password": "MatKhauMoi456"},
            headers={"Authorization": f"Bearer {access}"},
        )

        assert phan_hoi.status_code == 204
        lai = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": "MatKhauMoi456"},
        )
        assert lai.status_code == 200

    async def test_mat_khau_hien_tai_sai_bi_tu_choi(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        access = dang_nhap.json()["access_token"]

        phan_hoi = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "SaiRoi123", "new_password": "MatKhauMoi456"},
            headers={"Authorization": f"Bearer {access}"},
        )

        assert phan_hoi.status_code == 400

    async def test_doi_mat_khau_thu_hoi_moi_phien(
        self, client: AsyncClient, engine: AsyncEngine
    ) -> None:
        await _tao_admin(engine)
        dang_nhap = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@congty.vn", "password": MAT_KHAU},
        )
        access = dang_nhap.json()["access_token"]
        refresh = dang_nhap.json()["refresh_token"]

        await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": MAT_KHAU, "new_password": "MatKhauMoi456"},
            headers={"Authorization": f"Bearer {access}"},
        )

        lam_moi = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert lam_moi.status_code == 401
