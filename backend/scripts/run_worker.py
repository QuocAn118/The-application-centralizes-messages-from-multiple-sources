"""Khởi động worker xử lý job nền (phân tích LLM của #2).

**Đây là tiến trình RIÊNG, chạy song song với web server.** Không bật worker thì
webhook vẫn nhận tin bình thường, nhưng job phân tích nằm mãi trong hàng đợi và
mọi hội thoại ở lại ``CHO_PHAN`` — không có lỗi nào hiện ra, chỉ là AI không bao
giờ chạy. Đây là cái bẫy dễ gặp nhất khi dựng môi trường dev.

Chạy:
    uv run python -m scripts.run_worker
    uv run python -m scripts.run_worker --concurrency 4

Dừng bằng Ctrl+C: worker chờ job đang chạy xong rồi mới thoát, không bỏ dở.
"""

import argparse
import logging
import sys

from src.jobs.app import app
from src.shared.infrastructure.config import get_settings
from src.shared.infrastructure.event_loop import chay_async
from src.shared.infrastructure.logging import cau_hinh_logging

logger = logging.getLogger(__name__)


def _cho_phep_tieng_viet() -> None:
    """Cho console Windows in được tiếng Việt (cp1252 không mã hoá nổi chữ có dấu)."""
    for luong in (sys.stdout, sys.stderr):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8", errors="replace")


async def chay_worker(concurrency: int) -> None:
    """Mở kết nối hàng đợi rồi chạy worker cho tới khi bị dừng."""
    async with app.open_async():
        await app.run_worker_async(queues=["phan_tich"], concurrency=concurrency)


def main() -> int:
    _cho_phep_tieng_viet()
    bo_doc = argparse.ArgumentParser(description="Worker xử lý job nền của OmniChat.")
    bo_doc.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Số job chạy song song (mặc định 2). Mỗi job là một lời gọi LLM.",
    )
    tham_so = bo_doc.parse_args()

    settings = get_settings()
    cau_hinh_logging(settings.log_level)

    logger.info(
        "Worker khởi động — hàng đợi 'phan_tich', concurrency=%d, LLM_PROVIDER=%s",
        tham_so.concurrency,
        settings.llm_provider,
    )
    try:
        chay_async(chay_worker(tham_so.concurrency))
    except KeyboardInterrupt:
        logger.info("Worker đã dừng.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
