"""BE-5 qua HTTP thật: ghi chú nội bộ giới hạn theo phòng (GĐ1 §10.4).

Dựng một khách có hội thoại ở CẢ phòng A lẫn phòng B — cả hai phòng đều "đụng
được" khách — rồi kiểm mỗi phòng chỉ đọc ghi chú của phòng mình.
"""

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


async def _phong(c: AsyncClient, admin: str, ten: str) -> str:
    r = await c.post(
        "/api/v1/departments", json={"name": ten, "description": None}, headers=_bearer(admin)
    )
    return r.json()["id"]


async def _tin(c: AsyncClient, msg_id: str) -> None:
    raw = _webhook_zalo("oa_note", "khach_note", msg_id, "xin chao")
    r = await c.post(
        "/api/v1/webhooks/ZALO", content=raw, headers={"X-ZEvent-Signature": _ky_zalo(raw)}
    )
    assert r.status_code == 200


async def _hoi_thoai_cho_phan(c: AsyncClient, admin: str) -> dict:
    items = (
        await c.get("/api/v1/inbox", params={"status": "CHO_PHAN"}, headers=_bearer(admin))
    ).json()["items"]
    (ht,) = items
    return ht


async def test_moi_phong_chi_doc_ghi_chu_cua_minh(
    client_inbox: AsyncClient,  # noqa: F811
    engine: AsyncEngine,
) -> None:
    c = client_inbox
    await _tao_admin(engine)
    admin = await _dang_nhap_admin(c)
    phong_a, phong_b = await _phong(c, admin, "Phong A"), await _phong(c, admin, "Phong B")
    staff_a = await _tao_nhan_vien(c, admin, "a@congty.vn", "STAFF", phong_a)
    staff_a2 = await _tao_nhan_vien(c, admin, "a2@congty.vn", "STAFF", phong_a)
    staff_b = await _tao_nhan_vien(c, admin, "b@congty.vn", "STAFF", phong_b)
    await c.post(
        "/api/v1/channels",
        json={
            "platform": "ZALO",
            "external_channel_id": "oa_note",
            "name": "OA",
            "credential": "t",
        },
        headers=_bearer(admin),
    )

    # Hội thoại 1 → phòng A, đóng; khách nhắn lại → hội thoại 2 → phòng B.
    await _tin(c, "m1")
    ht1 = await _hoi_thoai_cho_phan(c, admin)
    khach = ht1["customer_id"]
    url1 = f"/api/v1/inbox/{ht1['conversation_id']}"
    await c.post(f"{url1}/assign", json={"department_id": phong_a}, headers=_bearer(admin))
    await c.post(f"{url1}/close", headers=_bearer(admin))
    await _tin(c, "m2")
    ht2 = await _hoi_thoai_cho_phan(c, admin)
    assert ht2["customer_id"] == khach
    await c.post(
        f"/api/v1/inbox/{ht2['conversation_id']}/assign",
        json={"department_id": phong_b},
        headers=_bearer(admin),
    )

    url = f"/api/v1/customers/{khach}/notes"
    r = await c.post(url, json={"body": "  Khach VIP phong A  "}, headers=_bearer(staff_a))
    assert r.status_code == 201, r.text
    note_a = r.json()
    assert (note_a["body"], note_a["department_name"], note_a["author_name"]) == (
        "Khach VIP phong A",
        "Phong A",
        "NV",
    )
    r = await c.post(url, json={"body": "Ghi chu phong B"}, headers=_bearer(staff_b))
    note_b = r.json()
    await c.post(url, json={"body": "Ghi chu admin"}, headers=_bearer(admin))

    # Nhân viên phòng A KHÔNG đọc được ghi chú phòng B (và ngược lại).
    doc_a = [n["body"] for n in (await c.get(url, headers=_bearer(staff_a))).json()]
    doc_b = [n["body"] for n in (await c.get(url, headers=_bearer(staff_b))).json()]
    assert doc_a == ["Khach VIP phong A"]
    assert doc_b == ["Ghi chu phong B"]
    # Admin thấy tất cả, mới trước.
    doc_admin = [n["body"] for n in (await c.get(url, headers=_bearer(admin))).json()]
    assert doc_admin == ["Ghi chu admin", "Ghi chu phong B", "Khach VIP phong A"]

    # Xoá: phòng khác → 404 (không lộ); cùng phòng khác người → 403; người viết → 204.
    assert (
        await c.delete(f"/api/v1/notes/{note_b['id']}", headers=_bearer(staff_a))
    ).status_code == 404
    assert (
        await c.delete(f"/api/v1/notes/{note_a['id']}", headers=_bearer(staff_a2))
    ).status_code == 403
    assert (
        await c.delete(f"/api/v1/notes/{note_a['id']}", headers=_bearer(staff_a))
    ).status_code == 204
    assert (await c.get(url, headers=_bearer(staff_a))).json() == []

    # Ghi chú rỗng → 422.
    assert (await c.post(url, json={"body": "   "}, headers=_bearer(staff_b))).status_code == 422


async def test_khach_ngoai_pham_vi_la_404(
    client_inbox: AsyncClient,  # noqa: F811
    engine: AsyncEngine,
) -> None:
    c = client_inbox
    await _tao_admin(engine)
    admin = await _dang_nhap_admin(c)
    phong_a, phong_b = await _phong(c, admin, "Phong A"), await _phong(c, admin, "Phong B")
    staff_b = await _tao_nhan_vien(c, admin, "b@congty.vn", "STAFF", phong_b)
    await c.post(
        "/api/v1/channels",
        json={
            "platform": "ZALO",
            "external_channel_id": "oa_note",
            "name": "OA",
            "credential": "t",
            "department_id": phong_a,
        },
        headers=_bearer(admin),
    )
    await _tin(c, "m1")
    (ht,) = (await c.get("/api/v1/inbox", headers=_bearer(admin))).json()["items"]
    url = f"/api/v1/customers/{ht['customer_id']}/notes"

    # Khách chỉ có hội thoại phòng A → nhân viên phòng B như không có khách này.
    assert (await c.get(url, headers=_bearer(staff_b))).status_code == 404
    assert (await c.post(url, json={"body": "x"}, headers=_bearer(staff_b))).status_code == 404
