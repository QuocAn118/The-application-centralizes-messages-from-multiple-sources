import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


class TestKiemTraSucKhoe:
    async def test_health_tra_ve_ok(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/health")

        assert phan_hoi.status_code == 200
        assert phan_hoi.json() == {"status": "ok"}

    async def test_health_ready_kiem_tra_co_so_du_lieu(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/health/ready")

        assert phan_hoi.status_code == 200
        assert phan_hoi.json()["database"] == "ok"


class TestHeaderBaoMat:
    async def test_co_day_du_header_bao_mat(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/health")

        assert phan_hoi.headers["X-Content-Type-Options"] == "nosniff"
        assert phan_hoi.headers["X-Frame-Options"] == "DENY"
        assert phan_hoi.headers["Referrer-Policy"] == "no-referrer"


class TestMaDinhDanhRequest:
    async def test_moi_phan_hoi_deu_co_request_id(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/health")

        assert phan_hoi.headers.get("X-Request-ID")

    async def test_giu_nguyen_request_id_do_client_gui(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/health", headers={"X-Request-ID": "ma-tu-client-123"})

        assert phan_hoi.headers["X-Request-ID"] == "ma-tu-client-123"


class TestDinhDangLoi:
    async def test_khong_tim_thay_duong_dan(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/api/v1/duong-dan-khong-ton-tai")

        assert phan_hoi.status_code == 404

    async def test_thieu_token_tra_ve_401_dung_dinh_dang(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/api/v1/auth/me")

        assert phan_hoi.status_code == 401
        noi_dung = phan_hoi.json()
        assert noi_dung["error"]["code"] == "MISSING_CREDENTIALS"
        assert "request_id" in noi_dung

    async def test_token_rac_tra_ve_401(self, client: AsyncClient) -> None:
        phan_hoi = await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer token-bia-dat"}
        )

        assert phan_hoi.status_code == 401
        assert phan_hoi.json()["error"]["code"] == "INVALID_TOKEN"


class TestTaiLieuApi:
    async def test_co_openapi_schema(self, client: AsyncClient) -> None:
        phan_hoi = await client.get("/openapi.json")

        assert phan_hoi.status_code == 200
        assert phan_hoi.json()["info"]["title"] == "OmniChat API"
