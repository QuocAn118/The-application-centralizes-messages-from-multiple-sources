"""Một kịch bản duy nhất đi qua toàn bộ vòng đời của hệ thống.

Test này tồn tại để bắt lỗi tích hợp giữa các thành phần — thứ mà test đơn lẻ
không thấy được.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

MAT_KHAU_ADMIN = "MatKhauAdmin123"
MAT_KHAU_TAM = "MatKhauTam123"


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
            {
                "id": new_id(),
                "hash": BcryptPasswordHasher(rounds=4).hash(MAT_KHAU_ADMIN),
            },
        )


async def test_vong_doi_day_du_cua_he_thong(client: AsyncClient, engine: AsyncEngine) -> None:
    await _tao_admin(engine)

    # 1. Quản trị viên đăng nhập
    dn = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@congty.vn", "password": MAT_KHAU_ADMIN},
    )
    assert dn.status_code == 200
    admin_token = dn.json()["access_token"]

    # 2. Tạo phòng ban
    phong = await client.post(
        "/api/v1/departments",
        json={"name": "Tư vấn sản phẩm A", "description": "Phòng tư vấn"},
        headers=_bearer(admin_token),
    )
    assert phong.status_code == 201
    phong_id = phong.json()["id"]

    # 3. Tạo quản lý cho phòng
    ql = await client.post(
        "/api/v1/users",
        json={
            "email": "quanly@congty.vn",
            "full_name": "Trần Quản Lý",
            "role": "MANAGER",
            "department_id": phong_id,
            "password": MAT_KHAU_TAM,
        },
        headers=_bearer(admin_token),
    )
    assert ql.status_code == 201

    # 4. Tạo nhân viên
    nv = await client.post(
        "/api/v1/users",
        json={
            "email": "nhanvien@congty.vn",
            "full_name": "Lê Nhân Viên",
            "role": "STAFF",
            "department_id": phong_id,
            "password": MAT_KHAU_TAM,
        },
        headers=_bearer(admin_token),
    )
    assert nv.status_code == 201
    nv_id = nv.json()["id"]

    # 5. Nhân viên đăng nhập lần đầu, được báo phải đổi mật khẩu
    nv_dn = await client.post(
        "/api/v1/auth/login",
        json={"email": "nhanvien@congty.vn", "password": MAT_KHAU_TAM},
    )
    assert nv_dn.json()["must_change_password"] is True
    nv_token = nv_dn.json()["access_token"]

    # 6. Nhân viên đổi mật khẩu
    doi = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": MAT_KHAU_TAM, "new_password": "MatKhauRieng456"},
        headers=_bearer(nv_token),
    )
    assert doi.status_code == 204

    # 7. Đăng nhập bằng mật khẩu mới, không còn bị bắt đổi
    nv_dn2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "nhanvien@congty.vn", "password": "MatKhauRieng456"},
    )
    assert nv_dn2.json()["must_change_password"] is False
    nv_token = nv_dn2.json()["access_token"]

    # 8. Nhân viên không gọi được endpoint quản trị
    cam = await client.post(
        "/api/v1/users",
        json={
            "email": "tuy_tien@congty.vn",
            "full_name": "Tự tạo",
            "role": "STAFF",
            "department_id": phong_id,
            "password": MAT_KHAU_TAM,
        },
        headers=_bearer(nv_token),
    )
    assert cam.status_code == 403

    # 9. Quản lý thấy được nhân viên phòng mình
    ql_dn = await client.post(
        "/api/v1/auth/login",
        json={"email": "quanly@congty.vn", "password": MAT_KHAU_TAM},
    )
    ql_token = ql_dn.json()["access_token"]
    ds = await client.get("/api/v1/users", headers=_bearer(ql_token))
    assert "nhanvien@congty.vn" in {u["email"] for u in ds.json()["items"]}

    # 10. Quản trị viên nâng nhân viên lên quản lý — bị chặn vì phòng đã có
    nang = await client.patch(
        f"/api/v1/users/{nv_id}/role",
        json={"role": "MANAGER", "department_id": phong_id},
        headers=_bearer(admin_token),
    )
    assert nang.status_code == 422
    assert nang.json()["error"]["code"] == "DEPARTMENT_ALREADY_HAS_MANAGER"

    # 11. Vô hiệu hoá nhân viên
    vhh = await client.post(f"/api/v1/users/{nv_id}/deactivate", headers=_bearer(admin_token))
    assert vhh.status_code == 200
    assert vhh.json()["is_active"] is False

    # 12. Nhân viên đã nghỉ không đăng nhập được nữa
    thu_lai = await client.post(
        "/api/v1/auth/login",
        json={"email": "nhanvien@congty.vn", "password": "MatKhauRieng456"},
    )
    assert thu_lai.status_code == 400
    assert thu_lai.json()["error"]["code"] == "INACTIVE_ACCOUNT"

    # 13. Kích hoạt lại
    kh = await client.post(f"/api/v1/users/{nv_id}/reactivate", headers=_bearer(admin_token))
    assert kh.status_code == 200
    assert kh.json()["is_active"] is True

    # 14. Nhật ký ghi nhận đủ mọi thao tác
    nk = await client.get("/api/v1/audit-logs", headers=_bearer(admin_token))
    hanh_dong = {e["action"] for e in nk.json()["items"]}
    assert {
        "department.created",
        "user.created",
        "user.deactivated",
        "user.reactivated",
        "auth.login_succeeded",
        "user.password_changed",
    } <= hanh_dong


async def test_khong_bao_gio_lo_hash_mat_khau_qua_api(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """Quét mọi phản hồi để chắc chắn không có chuỗi hash nào lọt ra."""
    await _tao_admin(engine)
    dn = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@congty.vn", "password": MAT_KHAU_ADMIN},
    )
    token = dn.json()["access_token"]

    phong = await client.post(
        "/api/v1/departments", json={"name": "Phòng A"}, headers=_bearer(token)
    )
    tao = await client.post(
        "/api/v1/users",
        json={
            "email": "x@congty.vn",
            "full_name": "Người X",
            "role": "STAFF",
            "department_id": phong.json()["id"],
            "password": MAT_KHAU_TAM,
        },
        headers=_bearer(token),
    )

    cac_phan_hoi = [
        dn.text,
        phong.text,
        tao.text,
        (await client.get("/api/v1/auth/me", headers=_bearer(token))).text,
        (await client.get("/api/v1/users", headers=_bearer(token))).text,
        (await client.get("/api/v1/audit-logs", headers=_bearer(token))).text,
    ]

    for noi_dung in cac_phan_hoi:
        assert "$2b$" not in noi_dung
        assert "password_hash" not in noi_dung
        assert MAT_KHAU_TAM not in noi_dung
        assert MAT_KHAU_ADMIN not in noi_dung
