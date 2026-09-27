"""Gieo dữ liệu cho các kịch bản kiểm chứng giao diện (Playwright) — CHỈ môi trường dev.

Vì sao có script này: các kịch bản kiểm chứng từng hỏng vì dữ liệu dev bị đổi tay
(ca bị huỷ, đơn đã duyệt hết, mật khẩu tạm đã bị đổi). Chạy script này trước mỗi
đợt kiểm chứng để đưa dữ liệu về đúng trạng thái kịch bản cần.

**Chỉ đi qua API công khai** (không ghi thẳng database): mọi thứ tạo ra đều qua
đúng quy tắc nghiệp vụ, và script chỉ đụng được backend nó được trỏ tới — mà nó
TỪ CHỐI chạy nếu backend không nằm ở localhost.

Idempotent: chạy nhiều lần ra cùng trạng thái. Tạo nếu thiếu, sửa nếu lệch:
- 3 phòng kiểm chứng (A, B, và một phòng riêng cho tài khoản mật khẩu tạm).
- Tài khoản dùng thường (mật khẩu cố định, KHÔNG bắt đổi): Admin, Manager A,
  Manager B, Staff A.
- 2 tài khoản **đang chờ đổi mật khẩu tạm** (Manager, Staff) — đưa về lại trạng
  thái này MỖI lần chạy, vì kịch bản `ui-f2.mjs` đổi mật khẩu của chúng.
- Mẫu ca 08:00-17:00 ở phòng A + 1 ca ACTIVE của Staff A trong tháng hiện tại;
  mẫu ca ở phòng B + 1 ca ACTIVE của Manager B (người có ca, KHÔNG có mục tiêu KPI).
- Mục tiêu KPI "hội thoại đã đóng" của Staff A cho tháng hiện tại.
- 1 đơn CHỜ DUYỆT của Staff A và của Manager A (kịch bản duyệt/từ chối tiêu thụ).

Chạy (backend phải đang chạy):
    cd backend
    uv run python -m scripts.seed_kiem_chung
    uv run python -m scripts.seed_kiem_chung --api http://127.0.0.1:8003/api/v1

Tài khoản Admin để bắt đầu: biến môi trường ``SEED_ADMIN_EMAIL`` /
``SEED_ADMIN_PASSWORD`` (mặc định: tài khoản kiểm chứng ``kiemchung.f2``). Nếu
đăng nhập Admin hỏng, đặt lại bằng ``uv run python -m scripts.reset_password``.
"""

import argparse
import calendar
import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlencode, urlparse

API_MAC_DINH = "http://127.0.0.1:8003/api/v1"

# Mật khẩu cố định của các tài khoản kiểm chứng dùng thường.
MAT_KHAU = "OmniTest2026!"
# Hai tài khoản chờ đổi mật khẩu: mật khẩu TẠM (seed đặt lại) và mật khẩu MỚI
# (kịch bản ui-f2 đổi sang).
MAT_KHAU_TAM = "TamThoi2026!"
MAT_KHAU_MOI = "DaDoi2026!x"

PHONG_A = "Phong F3 A 76aa2a"
PHONG_B = "Phong F3 B 76aa2a"
# Phòng riêng cho tài khoản chờ đổi mật khẩu: backend chỉ cho MỘT Manager đang
# hoạt động mỗi phòng (DEPARTMENT_ALREADY_HAS_MANAGER), nên Manager tạm không ở
# chung phòng A với mgrA được.
PHONG_C = "Phong kiem chung mat khau tam"

# (email, họ tên, vai, phòng | None, chờ đổi mật khẩu?)
TAI_KHOAN: list[tuple[str, str, str, str | None, bool]] = [
    ("f3.mgra.76aa2a@congty.vn", "F3 mgrA", "MANAGER", PHONG_A, False),
    ("f3.mgrb.76aa2a@congty.vn", "F3 mgrB", "MANAGER", PHONG_B, False),
    ("f3.staffa.76aa2a@congty.vn", "F3 staffA", "STAFF", PHONG_A, False),
    ("kc.mgr.tam@congty.vn", "Kiểm chứng Quản lý tạm", "MANAGER", PHONG_C, True),
    ("kc.staff.tam@congty.vn", "Kiểm chứng Nhân viên tạm", "STAFF", PHONG_C, True),
]


class SeedError(Exception):
    pass


class Api:
    def __init__(self, goc: str) -> None:
        self.goc = goc.rstrip("/")

    def goi(
        self,
        phuong_thuc: str,
        duong: str,
        token: str | None = None,
        than: Any = None,
        kiem: tuple[int, ...] = (200, 201, 204),
    ) -> Any:
        du_lieu = json.dumps(than).encode() if than is not None else None
        yeu_cau = urllib.request.Request(self.goc + duong, data=du_lieu, method=phuong_thuc)
        yeu_cau.add_header("Content-Type", "application/json")
        if token:
            yeu_cau.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(yeu_cau, timeout=30) as phan_hoi:
                ma, tho = phan_hoi.status, phan_hoi.read().decode()
        except urllib.error.HTTPError as loi:
            ma, tho = loi.code, loi.read().decode()
        ket_qua = json.loads(tho) if tho else None
        if ma not in kiem:
            raise SeedError(f"{phuong_thuc} {duong} -> {ma}: {tho[:300]}")
        return ket_qua

    def dang_nhap(self, email: str, mat_khau: str) -> str:
        phan_hoi = self.goi("POST", "/auth/login", than={"email": email, "password": mat_khau})
        return str(phan_hoi["access_token"])


def bao_dam_localhost(goc: str) -> None:
    """Từ chối chạy nếu backend không ở máy này — script đặt lại mật khẩu thật."""
    may = urlparse(goc).hostname
    if may not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit(f"TỪ CHỐI: backend {goc} không ở localhost. Script này chỉ dành cho dev.")


def phong(api: Api, tk: str) -> dict[str, str]:
    """Bảo đảm hai phòng kiểm chứng tồn tại và đang hoạt động; trả tên -> id."""
    ds = api.goi("GET", "/departments?" + urlencode({"limit": 100, "offset": 0}), tk)["items"]
    theo_ten = {p["name"]: p for p in ds}
    ket_qua: dict[str, str] = {}
    for ten in (PHONG_A, PHONG_B, PHONG_C):
        p = theo_ten.get(ten)
        if p is None:
            p = api.goi(
                "POST", "/departments", tk, {"name": ten, "description": "Dữ liệu kiểm chứng"}
            )
            print(f"  + tạo phòng {ten}")
        elif not p.get("is_active", True):
            # Phòng ban không bật lại được (#F2) — báo rõ thay vì âm thầm dùng phòng chết.
            raise SeedError(f"Phòng '{ten}' đã bị vô hiệu hoá và không bật lại được.")
        ket_qua[ten] = p["id"]
    return ket_qua


def tim_nguoi(api: Api, tk: str, email: str) -> dict[str, Any] | None:
    ds = api.goi("GET", "/users?" + urlencode({"search": email, "limit": 20, "offset": 0}), tk)[
        "items"
    ]
    return next((u for u in ds if u["email"].lower() == email.lower()), None)


def tai_khoan(api: Api, tk: str, id_phong: dict[str, str]) -> dict[str, str]:
    """Tạo/sửa tài khoản kiểm chứng; đặt mật khẩu và trạng thái chờ-đổi đúng yêu cầu."""
    ids: dict[str, str] = {}
    for email, ten, vai, ten_phong, cho_doi in TAI_KHOAN:
        dept = id_phong[ten_phong] if ten_phong else None
        u = tim_nguoi(api, tk, email)
        tam = MAT_KHAU_TAM if cho_doi else "Tam-" + secrets.token_urlsafe(9) + "1a"
        if u is None:
            u = api.goi(
                "POST",
                "/users",
                tk,
                {
                    "email": email,
                    "full_name": ten,
                    "role": vai,
                    "department_id": dept,
                    "password": tam,
                },
            )
            print(f"  + tạo {email}")
        else:
            if not u["is_active"]:
                api.goi("POST", f"/users/{u['id']}/reactivate", tk)
                print(f"  ~ kích hoạt lại {email}")
            if u["role"] != vai:
                api.goi("PATCH", f"/users/{u['id']}/role", tk, {"role": vai})
                print(f"  ~ đổi vai {email} -> {vai}")
            if u.get("department_id") != dept:
                api.goi("PATCH", f"/users/{u['id']}/department", tk, {"department_id": dept})
                print(f"  ~ đổi phòng {email}")
            # Đặt lại = mật khẩu tạm + bắt đổi (quy tắc reset của Admin).
            api.goi("POST", f"/users/{u['id']}/reset-password", tk, {"new_password": tam})
        if not cho_doi:
            # Đăng nhập bằng mật khẩu tạm rồi tự đổi sang mật khẩu cố định: đi đúng
            # luồng người dùng thật, và xoá cờ bắt đổi.
            tk_nguoi = api.dang_nhap(email, tam)
            api.goi(
                "POST",
                "/auth/change-password",
                tk_nguoi,
                {"current_password": tam, "new_password": MAT_KHAU},
            )
        ids[email] = u["id"]
        print(f"  = {email:32} {'CHỜ ĐỔI (' + MAT_KHAU_TAM + ')' if cho_doi else 'sẵn sàng'}")
    return ids


def bao_dam_ca(api: Api, tk: str, id_phong: str, id_user: str, nhan: str) -> None:
    """Mẫu ca 08:00-17:00 ở ``id_phong`` + ≥1 buổi ca ACTIVE của ``id_user`` trong tháng này."""
    hom_nay = date.today()
    ds_ca = api.goi("GET", "/shifts?is_active=true", tk)
    ca = next(
        (
            c
            for c in ds_ca
            if c["department_id"] == id_phong
            and str(c["start_time"]).startswith("08:00")
            and str(c["end_time"]).startswith("17:00")
        ),
        None,
    )
    if ca is None:
        ca = api.goi(
            "POST",
            "/shifts",
            tk,
            {
                "name": "Ca hành chính kiểm chứng",
                "start_time": "08:00",
                "end_time": "17:00",
                "department_id": id_phong,
            },
        )
        print(f"  + tạo mẫu ca 08:00-17:00 ({nhan})")

    dau = hom_nay.replace(day=1)
    cuoi = hom_nay.replace(day=calendar.monthrange(hom_nay.year, hom_nay.month)[1])
    lich = api.goi(
        "GET",
        "/shift-assignments?"
        + urlencode({"date_from": dau.isoformat(), "date_to": cuoi.isoformat()}),
        tk,
    )
    co_ca = any(p["user_id"] == id_user and p["status"] == "ACTIVE" for p in lich)
    if not co_ca:
        # Không phân ca lùi ngày: chọn hôm nay (luôn nằm trong tháng này).
        api.goi(
            "POST",
            "/shift-assignments",
            tk,
            {"shift_id": ca["id"], "user_id": id_user, "work_date": hom_nay.isoformat()},
        )
        print(f"  + phân ca {nhan} ngày {hom_nay.isoformat()}")


def ca_va_kpi(api: Api, tk: str, id_phong: dict[str, str], ids: dict[str, str]) -> None:
    """Ca + KPI cho các kịch bản Nhân sự và Báo cáo Ca & KPI.

    - Staff A (phòng A): 1 ca ACTIVE trong tháng + mục tiêu KPI tháng này.
    - Manager B (phòng B): 1 ca ACTIVE trong tháng và **KHÔNG BAO GIỜ** có mục tiêu
      KPI — dòng "có ca, chưa đặt mục tiêu" (null/null → "—") của báo cáo Ca & KPI
      (``ui-f5-gd2``). Phòng B vì kịch bản KPI (``ui-f3-gd3``) đặt mục tiêu trong
      phòng A. Trước đây dòng này sống nhờ dữ liệu tay ngoài seed.
    """
    hom_nay = date.today()
    id_staff = ids["f3.staffa.76aa2a@congty.vn"]
    bao_dam_ca(api, tk, id_phong[PHONG_A], id_staff, "Staff A")
    bao_dam_ca(api, tk, id_phong[PHONG_B], ids["f3.mgrb.76aa2a@congty.vn"], "Manager B")

    # POST /kpi-targets là UPSERT (#F3) — gọi lại không nhân bản.
    api.goi(
        "POST",
        "/kpi-targets",
        tk,
        {
            "subject_type": "USER",
            "subject_id": id_staff,
            "metric_type": "CONVERSATIONS_CLOSED",
            "period_year": hom_nay.year,
            "period_month": hom_nay.month,
            "target_value": "99",
        },
    )
    print(f"  = KPI Staff A tháng {hom_nay.month}/{hom_nay.year}")


def don_cho_duyet(api: Api) -> None:
    """Mỗi người (Staff A, Manager A) có đúng ≥1 đơn CHỜ DUYỆT mang lý do kiểm chứng."""
    thang_sau = (date.today().replace(day=28) + timedelta(days=4)).replace(day=1)
    for nhan, email in (
        ("staffA", "f3.staffa.76aa2a@congty.vn"),
        ("mgrA", "f3.mgra.76aa2a@congty.vn"),
    ):
        tk = api.dang_nhap(email, MAT_KHAU)
        ly_do = f"Don kiem chung cua {nhan}"
        dang_cho = api.goi(
            "GET", "/requests?" + urlencode({"status": "CHO_DUYET", "limit": 100, "offset": 0}), tk
        )["items"]
        if any(d["reason"] == ly_do for d in dang_cho):
            print(f"  = đã có đơn chờ duyệt của {nhan}")
            continue
        api.goi(
            "POST",
            "/requests",
            tk,
            {
                "request_type": "NGHI_PHEP",
                "reason": ly_do,
                "leave_start": thang_sau.isoformat(),
                "leave_end": (thang_sau + timedelta(days=2)).isoformat(),
            },
        )
        print(f"  + đơn chờ duyệt của {nhan}")


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8", errors="replace")

    bo_doc = argparse.ArgumentParser(description="Gieo dữ liệu kiểm chứng (chỉ dev).")
    bo_doc.add_argument("--api", default=os.environ.get("SEED_API", API_MAC_DINH))
    tham_so = bo_doc.parse_args()
    bao_dam_localhost(tham_so.api)

    api = Api(tham_so.api)
    email_admin = os.environ.get("SEED_ADMIN_EMAIL", "kiemchung.f2@congty.vn")
    mk_admin = os.environ.get("SEED_ADMIN_PASSWORD", MAT_KHAU)
    print(f"Gieo dữ liệu kiểm chứng vào {tham_so.api}")
    try:
        tk = api.dang_nhap(email_admin, mk_admin)
        id_phong = phong(api, tk)
        ids = tai_khoan(api, tk, id_phong)
        ca_va_kpi(api, tk, id_phong, ids)
        don_cho_duyet(api)
    except SeedError as loi:
        print(f"LỖI: {loi}")
        return 1

    print("\nBiến môi trường cho các kịch bản ui-*.mjs:")
    print(f'  ADMIN_EMAIL="{email_admin}" ADMIN_PASS="{mk_admin}" PASS="{MAT_KHAU}"')
    print('  MGRA_EMAIL="f3.mgra.76aa2a@congty.vn" MGRB_EMAIL="f3.mgrb.76aa2a@congty.vn"')
    print('  STAFFA_EMAIL="f3.staffa.76aa2a@congty.vn"')
    for vai, email in (("MGR", "kc.mgr.tam@congty.vn"), ("STAFF", "kc.staff.tam@congty.vn")):
        print(
            f'  {vai}_EMAIL="{email}" {vai}_PASS="{MAT_KHAU_TAM}" {vai}_NEW_PASS="{MAT_KHAU_MOI}"'
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
