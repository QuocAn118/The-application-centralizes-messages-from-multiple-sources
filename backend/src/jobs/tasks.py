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
