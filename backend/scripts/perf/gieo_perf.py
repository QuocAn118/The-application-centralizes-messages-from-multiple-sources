"""Dựng database ĐO HIỆU NĂNG riêng `omnichat_perf` và gieo dữ liệu lớn (Phần 2a).

Vì sao DB riêng: đo `GET /inbox` với hàng nghìn hội thoại mà gieo vào DB dev thì
Hộp thư, Báo cáo của user ngập dữ liệu giả. Script TỪ CHỐI chạy nếu tên DB không
phải đúng `omnichat_perf`.

Gieo: 3 phòng, 30 nhân viên (+1 Admin), 3 kênh, 3.000 hội thoại, ~20 tin/hội thoại
xen vào/ra; 20% chưa có người phụ trách, 10% đã đóng, 5% chờ phân.
Ba tài khoản đăng nhập để đo (mật khẩu `PerfTest2026!`):
    perf.admin@congty.vn · perf.mgr0@congty.vn · perf.staff0@congty.vn

Chạy (tuần tự):
    cd backend
    uv run python -m scripts.perf.gieo_perf            # tạo DB + migrate + gieo
    DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/omnichat_perf \\
      uv run python -m scripts.run_server --port 8013  # backend đo
"""

import os
import random
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import psycopg

from src.modules.identity.infrastructure.security.password_hasher import BcryptPasswordHasher

TEN_DB = "omnichat_perf"
URL_SQLA = f"postgresql+psycopg://postgres@localhost:5432/{TEN_DB}"
URL_PG = f"postgresql://postgres@localhost:5432/{TEN_DB}"
URL_QUAN_TRI = "postgresql://postgres@localhost:5432/postgres"
MAT_KHAU = "PerfTest2026!"

SO_HOI_THOAI = 3000
TIN_MOI_HOI_THOAI = 20


def tao_db() -> None:
    with psycopg.connect(URL_QUAN_TRI, autocommit=True) as c:
        co = c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEN_DB,)).fetchone()
        if co:
            print(f"DB {TEN_DB} đã có — xoá và dựng lại cho số đo sạch.")
            c.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (TEN_DB,),
            )
            c.execute(f'DROP DATABASE "{TEN_DB}"')
        c.execute(f'CREATE DATABASE "{TEN_DB}"')
    moi_truong = {**os.environ, "DATABASE_URL": URL_SQLA}
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True, env=moi_truong)


def gieo() -> None:
    random.seed(20260927)
    bay_gio = datetime.now(UTC)
    hash_mk = BcryptPasswordHasher().hash(MAT_KHAU)
    phong = [uuid4() for _ in range(3)]
    kenh = [uuid4() for _ in range(3)]

    with psycopg.connect(URL_PG) as c, c.cursor() as cur:
        for i, p in enumerate(phong):
            cur.execute(
                "INSERT INTO departments (id,name,is_active,created_at,updated_at)"
                " VALUES (%s,%s,true,%s,%s)",
                (p, f"Phong perf {i}", bay_gio, bay_gio),
            )
        nguoi: list[tuple[UUID, UUID]] = []  # (user_id, phong)
        tk: list[tuple[str, str, str, UUID | None]] = [
            ("perf.admin@congty.vn", "Perf Admin", "ADMIN", None)
        ]
        for i in range(30):
            p = phong[i % 3]
            vai = "MANAGER" if i < 3 else "STAFF"
            tk.append(
                (
                    f"perf.{'mgr' if i < 3 else 'staff'}{i if i < 3 else i - 3}@congty.vn",
                    f"Nhân viên perf {i}",
                    vai,
                    p,
                )
            )
        for email, ten, vai, phong_tk in tk:
            uid = uuid4()
            cur.execute(
                "INSERT INTO users (id,email,password_hash,full_name,role,department_id,"
                "is_active,must_change_password,created_at,updated_at)"
                " VALUES (%s,%s,%s,%s,%s,%s,true,false,%s,%s)",
                (uid, email, hash_mk, ten, vai, phong_tk, bay_gio, bay_gio),
            )
            if phong_tk is not None:
                nguoi.append((uid, phong_tk))
        for i, ma_kenh in enumerate(kenh):
            cur.execute(
                "INSERT INTO channels (id,platform,external_channel_id,name,credential,"
                "department_id,is_active,created_at,updated_at)"
                " VALUES (%s,'TELEGRAM',%s,%s,'x',%s,true,%s,%s)",
                (ma_kenh, f"perf-{i}", f"Kênh perf {i}", phong[i], bay_gio, bay_gio),
            )

        khach, hoi_thoai, tin = [], [], []
        for i in range(SO_HOI_THOAI):
            k = random.randrange(3)
            cid, conv = uuid4(), uuid4()
            khach.append((cid, kenh[k], "TELEGRAM", f"kh{i}", f"Khách perf {i}", bay_gio, bay_gio))
            r = random.random()
            if r < 0.05:
                status, dept, gan = "CHO_PHAN", None, None
            else:
                dept = phong[k]
                trong_phong = [u for u, p in nguoi if p == dept]
                gan = None if r < 0.25 else random.choice(trong_phong)
                status = "DA_DONG" if r > 0.90 else "DANG_MO"
            bat_dau = bay_gio - timedelta(minutes=random.randrange(1, 60 * 24 * 30))
            moc = bat_dau
            for j in range(TIN_MOI_HOI_THOAI + random.randrange(-5, 6)):
                moc += timedelta(minutes=random.randrange(1, 90))
                huong = "INBOUND" if j % 3 != 1 else "OUTBOUND"
                tin.append((uuid4(), conv, huong, f"tin {j}", None, None, moc))
            hoi_thoai.append(
                (
                    conv,
                    kenh[k],
                    cid,
                    status,
                    dept,
                    gan,
                    moc,
                    bat_dau,
                    moc,
                    moc if status == "DA_DONG" else None,
                )
            )

        with cur.copy(
            "COPY customers (id,channel_id,platform,external_id,display_name,"
            "created_at,updated_at) FROM STDIN"
        ) as cp:
            for dong_kh in khach:
                cp.write_row(dong_kh)
        with cur.copy(
            "COPY conversations (id,channel_id,customer_id,status,department_id,"
            "assigned_user_id,last_message_at,created_at,updated_at,closed_at)"
            " FROM STDIN"
        ) as cp:
            for dong_ht in hoi_thoai:
                cp.write_row(dong_ht)
        with cur.copy(
            "COPY messages (id,conversation_id,direction,text,external_message_id,"
            "sender_user_id,created_at) FROM STDIN"
        ) as cp:
            for dong_tin in tin:
                cp.write_row(dong_tin)
        c.commit()
        cur.execute("ANALYZE")
    print(f"Đã gieo {len(hoi_thoai)} hội thoại, {len(tin)} tin, {len(nguoi) + 1} tài khoản.")


if __name__ == "__main__":
    if TEN_DB != "omnichat_perf":  # chốt an toàn, không bao giờ đụng DB khác
        raise SystemExit("Từ chối: chỉ chạy trên omnichat_perf.")
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8", errors="replace")
    tao_db()
    gieo()
