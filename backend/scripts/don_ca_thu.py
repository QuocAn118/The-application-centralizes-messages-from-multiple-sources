"""Dọn mẫu ca do kịch bản kiểm chứng giao diện tạo ra — CHỈ môi trường dev.

Kịch bản ``ui-f3-gd2`` tạo một mẫu ca ``Ca GD2 <hậu tố>`` mỗi lần chạy và không
kịch bản nào dùng lại. API không có xoá mẫu ca (chỉ ngừng dùng), nên script này
xoá thẳng trong DB; buổi ca của chúng đi theo (FK ``ON DELETE CASCADE``).

Chỉ xoá đúng tên khớp ``^Ca GD2 [a-z0-9]+$`` — không đụng mẫu ca nào khác.

**Từ chối chạy** khi ``APP_ENV=production`` hoặc database không ở localhost.

Chạy:
    cd backend
    uv run python -m scripts.don_ca_thu
"""

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from src.shared.infrastructure.config import get_settings

MAU_TEN = r"^Ca GD2 [a-z0-9]+$"
MAY_CUC_BO = ("localhost", "127.0.0.1", "::1")


def ly_do_tu_choi(app_env: str, database_url: str) -> str | None:
    """Lý do KHÔNG được chạy, hoặc ``None`` nếu an toàn (dev + DB cục bộ)."""
    if app_env.strip().lower() in ("production", "prod"):
        return f"APP_ENV={app_env}"
    may = make_url(database_url).host
    if may not in MAY_CUC_BO:
        return f"database ở {may!r}, không phải localhost"
    return None


def _don(database_url: str) -> int:
    # Engine đồng bộ: script chạy một câu lệnh, không cần async (và async psycopg
    # không chạy với ProactorEventLoop mặc định trên Windows).
    engine = create_engine(database_url)
    try:
        with engine.begin() as conn:
            kq = conn.execute(text("DELETE FROM shifts WHERE name ~ :mau"), {"mau": MAU_TEN})
            return kq.rowcount
    finally:
        engine.dispose()


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8", errors="replace")
    settings = get_settings()
    ly_do = ly_do_tu_choi(settings.app_env, settings.database_url)
    if ly_do:
        print(f"TỪ CHỐI: {ly_do}. Script này chỉ dành cho dev.")
        return 2
    print(f"đã xoá {_don(settings.database_url)} mẫu ca 'Ca GD2 …'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
