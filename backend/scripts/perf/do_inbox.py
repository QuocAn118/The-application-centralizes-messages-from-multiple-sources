"""Đo thời gian `GET /inbox` trên backend đo (mặc định cổng 8013, DB omnichat_perf).

In p50 / p95 (ms) theo từng vai và từng kiểu lọc. Chạy trước và sau mỗi thay đổi
backend của Phần 2a để so; ngưỡng dừng: chậm thêm > 100 ms (spec 2a §3.3).

    uv run python -m scripts.perf.do_inbox [--api http://127.0.0.1:8013/api/v1] [--lan 30]
"""

import argparse
import json
import statistics
import sys
import time
import urllib.request

TAI_KHOAN = {
    "ADMIN": "perf.admin@congty.vn",
    "MANAGER": "perf.mgr0@congty.vn",
    "STAFF": "perf.staff0@congty.vn",
}
MAT_KHAU = "PerfTest2026!"


def goi(url: str, token: str | None = None, body: dict[str, str] | None = None) -> bytes:
    du_lieu = json.dumps(body).encode() if body else None
    yc = urllib.request.Request(url, data=du_lieu, method="POST" if body else "GET")
    yc.add_header("Content-Type", "application/json")
    if token:
        yc.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(yc, timeout=60) as ph:
        return bytes(ph.read())


def main() -> None:
    bo_doc = argparse.ArgumentParser()
    bo_doc.add_argument("--api", default="http://127.0.0.1:8013/api/v1")
    bo_doc.add_argument("--lan", type=int, default=30)
    bo_doc.add_argument("--loc", nargs="*", default=[""], help='vd: "" "assignee=me"')
    ts = bo_doc.parse_args()
    for vai, email in TAI_KHOAN.items():
        tk = json.loads(goi(f"{ts.api}/auth/login", body={"email": email, "password": MAT_KHAU}))
        token = tk["access_token"]
        for loc in ts.loc:
            url = f"{ts.api}/inbox?limit=25&offset=0" + (f"&{loc}" if loc else "")
            goi(url, token)  # làm nóng
            ms = []
            for _ in range(ts.lan):
                t0 = time.perf_counter()
                goi(url, token)
                ms.append((time.perf_counter() - t0) * 1000)
            ms.sort()
            p95 = ms[max(0, int(len(ms) * 0.95) - 1)]
            nhan = loc or "(khong loc)"
            print(f"{vai:8} {nhan:16} p50={statistics.median(ms):7.1f}ms  p95={p95:7.1f}ms")


if __name__ == "__main__":
    for luong in (sys.stdout,):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8", errors="replace")
    main()
