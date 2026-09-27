"""BE-7 qua HTTP thật: mẫu trả lời theo phòng + dùng chung."""

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.e2e.test_inbox_api import (  # noqa: F401  (fixture dùng qua tên)
    _bearer,
    _dang_nhap_admin,
    _tao_admin,
    _tao_nhan_vien,
    app_inbox,
    client_inbox,
)

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


async def test_pham_vi_mau_tra_loi(
    client_inbox: AsyncClient,  # noqa: F811
    engine: AsyncEngine,
) -> None:
    c = client_inbox
    await _tao_admin(engine)
    admin = await _dang_nhap_admin(c)

    async def phong(ten: str) -> str:
        r = await c.post(
            "/api/v1/departments", json={"name": ten, "description": None}, headers=_bearer(admin)
        )
        return r.json()["id"]

    phong_a, phong_b = await phong("Phong A"), await phong("Phong B")
    mgr_a = await _tao_nhan_vien(c, admin, "ma@congty.vn", "MANAGER", phong_a)
    staff_a = await _tao_nhan_vien(c, admin, "sa@congty.vn", "STAFF", phong_a)
    staff_b = await _tao_nhan_vien(c, admin, "sb@congty.vn", "STAFF", phong_b)
    url = "/api/v1/reply-templates"

    async def tao(tok: str, dept: str | None, title: str) -> Response:
        return await c.post(
            url,
            json={"department_id": dept, "title": title, "body": f"Noi dung {title}"},
            headers=_bearer(tok),
        )

    assert (await tao(admin, None, "Chao hoi")).status_code == 201
    r = await tao(mgr_a, phong_a, "Bao gia A")
    assert r.status_code == 201, r.text
    mau_a = r.json()
    assert (await tao(admin, phong_b, "Bao hanh B")).status_code == 201

    # Manager: không tạo mẫu dùng chung / phòng khác; Staff chỉ đọc.
    assert (await tao(mgr_a, None, "x")).json()["error"]["code"] == "TEMPLATE_SHARED_ADMIN_ONLY"
    assert (await tao(mgr_a, phong_b, "x")).json()["error"]["code"] == "TEMPLATE_OUT_OF_SCOPE"
    assert (await tao(staff_a, phong_a, "x")).status_code == 403

    async def thay(tok: str) -> list[str]:
        return [m["title"] for m in (await c.get(url, headers=_bearer(tok))).json()]

    assert await thay(staff_a) == ["Bao gia A", "Chao hoi"]
    assert await thay(staff_b) == ["Bao hanh B", "Chao hoi"]
    assert await thay(admin) == ["Bao gia A", "Bao hanh B", "Chao hoi"]

    # Sửa/xoá: mẫu phòng khác = 404 với người ngoài phòng; Manager sửa được mẫu phòng mình.
    assert (
        await c.patch(f"{url}/{mau_a['id']}", json={"title": "x"}, headers=_bearer(staff_b))
    ).status_code == 404
    sua = await c.patch(f"{url}/{mau_a['id']}", json={"body": "Gia moi"}, headers=_bearer(mgr_a))
    assert sua.json()["body"] == "Gia moi"
    assert (await c.delete(f"{url}/{mau_a['id']}", headers=_bearer(staff_a))).status_code == 403
    assert (await c.delete(f"{url}/{mau_a['id']}", headers=_bearer(mgr_a))).status_code == 204
    assert await thay(staff_a) == ["Chao hoi"]
