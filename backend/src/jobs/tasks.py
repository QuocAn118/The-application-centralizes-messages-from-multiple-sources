"""Task nền: phân tích hội thoại bằng LLM, tách khỏi request webhook.

**Vấn đề đã giải:** trước đây hook phân tích chạy ĐỒNG BỘ ngay trong webhook, nên
mỗi tin đến phải chờ LLM vài giây. Zalo/Meta/Telegram đều có timeout ngắn và sẽ
gửi lại khi quá hạn — tin không mất (idempotency của ``IngestInboundMessage`` giữ
đúng) nhưng mỗi lần gửi lại lại tốn thêm một lời gọi LLM.

**Cách giải:** webhook chỉ lưu tin rồi ``defer`` một job và trả 200 ngay; worker
ở tiến trình riêng gọi LLM. Job nằm trong PostgreSQL nên sống sót qua restart —
khác ``BackgroundTasks`` của FastAPI (chỉ nằm trong RAM, mất khi process chết).

**Idempotency (Procrastinate bảo đảm *at-least-once*, job có thể chạy lại):**
``AnalyzeConversation`` đã có sẵn guard RB-5 — hội thoại đã có bản ghi phân tích
thì bỏ qua, trừ khi ``force``. Task gọi với ``force=False`` nên chạy lại lần hai
không tạo phân tích trùng và không tự phân phòng lần nữa.
"""

import logging
from uuid import UUID

from procrastinate import RetryStrategy

from src.jobs.app import app

logger = logging.getLogger(__name__)

# Thử lại các lỗi tạm thời của LLM (mạng chập, quota 429, timeout) với khoảng
# chờ tăng dần. Hết lượt thì job thành "failed" và hội thoại NẰM YÊN ở CHO_PHAN
# — đúng hành vi khi thiếu API key, Manager phân tay như bình thường.
#
# LƯU Ý: ``max_attempts`` của Procrastinate đếm số lần THỬ LẠI *sau* lần chạy
# đầu, nên 3 ở đây nghĩa là tối đa 4 lần chạy (đã kiểm chứng bằng test). Tổng
# thời gian chờ xấu nhất khoảng 8 + 16 + 32 = 56 giây.
SO_LAN_THU = 3
CHO_TANG_DAN_GIAY = 8


@app.task(
    name="phan_tich_hoi_thoai",
    queue="phan_tich",
    retry=RetryStrategy(
        max_attempts=SO_LAN_THU,
        exponential_wait=CHO_TANG_DAN_GIAY,
    ),
)
async def phan_tich_hoi_thoai(conversation_id: str) -> None:
    """Chạy phân tích LLM cho một hội thoại đã lưu.

    Tham số là **chuỗi** vì payload job được lưu dạng JSON — ``UUID`` không
    serialize thẳng được. Đổi lại kiểu ngay đầu hàm để phần còn lại vẫn làm việc
    với ``UUID``.

    Cố ý KHÔNG nuốt lỗi như hook cũ: ở đây ném lỗi là đúng, vì nó kích hoạt cơ
    chế retry của hàng đợi. Chỉ khi hết lượt thử job mới thành "failed", và lúc
    đó hội thoại vẫn ở CHO_PHAN — không kẹt ở trạng thái không xác định.
    """
    from src.jobs.wiring import chay_phan_tich

    await chay_phan_tich(UUID(conversation_id))


@app.task(
    name="tu_gan_nhan_vien",
    queue="phan_tich",
    retry=RetryStrategy(
        max_attempts=SO_LAN_THU,
        exponential_wait=CHO_TANG_DAN_GIAY,
    ),
)
async def tu_gan_nhan_vien(conversation_id: str) -> None:
    """Chọn một nhân viên trong phòng của hội thoại và gán (#3).

    **Job RIÊNG, không gộp vào ``phan_tich_hoi_thoai``** (quyết định 2026-09-15,
    xem ADR). Hai việc hỏng vì hai lý do khác nhau: phân loại hỏng khi LLM lỗi,
    gán người hỏng khi DB/ca làm trục trặc. Gộp chung thì mỗi lần retry lại gọi
    lại LLM đã thành công, và job phải tự nhớ "đã phân loại xong nhưng gán lỗi" —
    đúng loại trạng thái nội bộ đã sinh ra lỗi NOT_ANALYZED hôm trước.

    Tách ra thì mỗi job retry đúng phần việc của nó và guard nằm ở dữ liệu thật
    (hội thoại đã có người chưa), không nằm trong bộ nhớ của job.

    Idempotent: chạy lại trên hội thoại đã có người phụ trách thì bỏ qua — chính
    hook #3 kiểm điều đó trước khi gán.
    """
    from src.jobs.wiring import chay_tu_gan

    await chay_tu_gan(UUID(conversation_id))
