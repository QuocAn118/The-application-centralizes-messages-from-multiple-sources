"""Đánh dấu ĐÃ ĐỌC tới thời điểm triển khai cho mọi người dùng — chạy MỘT lần khi lên BE-1.

Vì sao: bảng ``conversation_reads`` mới tạo thì rỗng, mà "không có dòng = chưa đọc tin
nào" → sau khi triển khai, mọi tin vào của hội thoại chưa đóng hiện là chưa đọc với
MỌI người (huy hiệu 99+). Script ghi ``last_read_at = <lúc chạy>`` cho mọi cặp
(người dùng đang hoạt động, hội thoại chưa đóng), để chỉ tin tới SAU lúc triển khai
mới là chưa đọc.

- Cặp ngoài phạm vi xem của người đó (phòng khác) cũng được ghi — vô hại: số chưa
  đọc chỉ tính trên hội thoại trong phạm vi.
- Upsert ``GREATEST`` như ``mark_read``: mốc đã có mà MỚI hơn thì giữ, không lùi.
- Hội thoại ``DA_DONG`` bỏ qua (luôn tính 0 chưa đọc).

**Mặc định là CHẠY THỬ:** chạy đúng câu lệnh trong transaction rồi ROLLBACK, in số
dòng sẽ ghi. Chỉ ghi thật khi có ``--ghi``.

Chạy (ngay sau ``alembic upgrade head``, trước khi mở lại cho người dùng):
    cd backend
    uv run python -m scripts.danh_dau_da_doc_khi_trien_khai          # chạy thử
    uv run python -m scripts.danh_dau_da_doc_khi_trien_khai --ghi    # ghi thật
"""

import sys
from datetime import UTC, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from src.shared.infrastructure.config import get_settings

CAU_GHI = """
INSERT INTO conversation_reads (user_id, conversation_id, last_read_at)
SELECT u.id, c.id, :moc
FROM users u CROSS JOIN conversations c
WHERE u.is_active AND c.status <> 'DA_DONG'
ON CONFLICT (user_id, conversation_id)
DO UPDATE SET last_read_at = GREATEST(conversation_reads.last_read_at, EXCLUDED.last_read_at)
"""


def chay(database_url: str, ghi: bool, moc: datetime) -> int:
    """Số dòng (người, hội thoại) được ghi/cập nhật. ``ghi=False`` → rollback."""
    # Engine đồng bộ như don_ca_thu: một câu lệnh, không cần async.
    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            tx = conn.begin()
            so = conn.execute(text(CAU_GHI), {"moc": moc}).rowcount
            if ghi:
                tx.commit()
            else:
                tx.rollback()
            return so
    finally:
        engine.dispose()


def main(argv: list[str]) -> int:
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8", errors="replace")
    ghi = "--ghi" in argv
    settings = get_settings()
    url = make_url(settings.database_url)
    moc = datetime.now(UTC)
    print(f"DB: {url.host}/{url.database} · APP_ENV={settings.app_env} · mốc {moc.isoformat()}")
    so = chay(settings.database_url, ghi, moc)
    if ghi:
        print(f"ĐÃ GHI {so} cặp (người dùng, hội thoại) — đã đọc tới mốc trên.")
    else:
        print(f"CHẠY THỬ: sẽ ghi {so} cặp (người dùng, hội thoại). Đã rollback, chưa ghi gì.")
        print("Ghi thật: thêm --ghi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
