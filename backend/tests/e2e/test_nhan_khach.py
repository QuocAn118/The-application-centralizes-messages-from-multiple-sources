"""BE-6 qua HTTP thật: nhãn dùng chung, màu chỉ từ bảng màu, gắn/gỡ cho khách."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.e2e.test_inbox_api import (  # noqa: F401  (fixture dùng qua tên)
    _bearer,
    _dang_nhap_admin,
    _ky_zalo,
    _tao_admin,
    _tao_nhan_vien,
    _webhook_zalo,
    app_inbox,
    client_inbox,
)

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


async def test_nhan_quan_ly_va_gan_cho_khach(
    client_inbox: AsyncClient,  # noqa: F811
    engine: AsyncEngine,
) -> None:
    c = client_inbox
    await _tao_admin(engine)
    admin = await _dang_nhap_admin(c)
    phong = (
        await c.post(
            "/api/v1/departments",
            json={"name": "Phong T", "description": None},
            headers=_bearer(admin),
        )
    ).json()["id"]
    manager = await _tao_nhan_vien(c, admin, "m@congty.vn", "MANAGER", phong)
    staff = await _tao_nhan_vien(c, admin, "s@congty.vn", "STAFF", phong)
    phong_khac = (
        await c.post(
            "/api/v1/departments",
            json={"name": "Phong Khac", "description": None},
            headers=_bearer(admin),
        )
    ).json()["id"]
    staff_khac = await _tao_nhan_vien(c, admin, "k@congty.vn", "STAFF", phong_khac)

    # Tạo / sửa: chỉ Manager/Admin; màu ngoài bảng → 422; trùng tên (hoa thường) → 409.
    tao = await c.post(
        "/api/v1/tags", json={"name": "  VIP   mới ", "color": "swatch-2"}, headers=_bearer(manager)
    )
    assert tao.status_code == 201, tao.text
    vip = tao.json()
    assert vip["name"] == "VIP mới"
    assert (
        await c.post(
            "/api/v1/tags", json={"name": "x", "color": "swatch-1"}, headers=_bearer(staff)
        )
    ).status_code == 403
    mau_la = await c.post(
        "/api/v1/tags", json={"name": "Đỏ", "color": "#ff0000"}, headers=_bearer(admin)
    )
    assert (mau_la.status_code, mau_la.json()["error"]["code"]) == (422, "TAG_COLOR_INVALID")
    trung = await c.post(
        "/api/v1/tags", json={"name": "vip MỚI", "color": "swatch-3"}, headers=_bearer(admin)
    )
    assert (trung.status_code, trung.json()["error"]["code"]) == (409, "TAG_NAME_TAKEN")
    cu = (
        await c.post(
            "/api/v1/tags", json={"name": "Khiếu nại", "color": "swatch-5"}, headers=_bearer(admin)
        )
    ).json()

    # Khách thuộc phòng T.
    await c.post(
        "/api/v1/channels",
        json={
            "platform": "ZALO",
            "external_channel_id": "oa_tag",
            "name": "OA",
            "credential": "t",
            "department_id": phong,
        },
        headers=_bearer(admin),
    )
    raw = _webhook_zalo("oa_tag", "khach_tag", "m1", "hi")
    await c.post(
        "/api/v1/webhooks/ZALO", content=raw, headers={"X-ZEvent-Signature": _ky_zalo(raw)}
    )
    (ht,) = (await c.get("/api/v1/inbox", headers=_bearer(admin))).json()["items"]
    url = f"/api/v1/customers/{ht['customer_id']}/tags"

    # Nhân viên gắn được; người ngoài phạm vi khách → 404.
    gan = await c.put(url, json={"tag_ids": [vip["id"], cu["id"]]}, headers=_bearer(staff))
    assert [t["name"] for t in gan.json()] == ["Khiếu nại", "VIP mới"]
    assert (await c.put(url, json={"tag_ids": []}, headers=_bearer(staff_khac))).status_code == 404

    # Ngừng dùng "Khiếu nại": biến khỏi danh sách chọn, khách đang có vẫn giữ;
    # nhưng không gắn MỚI được cho khách chưa có.
    await c.patch(f"/api/v1/tags/{cu['id']}", json={"is_active": False}, headers=_bearer(admin))
    ds = [t["name"] for t in (await c.get("/api/v1/tags", headers=_bearer(staff))).json()]
    assert ds == ["VIP mới"]
    giu = await c.put(url, json={"tag_ids": [cu["id"]]}, headers=_bearer(staff))
    assert [t["name"] for t in giu.json()] == ["Khiếu nại"]
    await c.put(url, json={"tag_ids": []}, headers=_bearer(staff))
    assert (
        await c.put(url, json={"tag_ids": [cu["id"]]}, headers=_bearer(staff))
    ).status_code == 404
    assert (await c.get(url, headers=_bearer(staff))).json() == []
