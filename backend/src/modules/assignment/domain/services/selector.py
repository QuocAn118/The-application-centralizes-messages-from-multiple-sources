"""Bộ chọn nhân viên nhận việc — logic thuần, không I/O.

Chuỗi tiêu chí THEO THỨ TỰ ƯU TIÊN (tiebreaker, không phải công thức trọng số);
dừng ở tiêu chí đầu tiên phá được hoà:

1. Đang trong ca — LỌC BẮT BUỘC: loại mọi ứng viên ngoài ca trước.
2. Tải hàng đợi thấp nhất — ``open_load`` nhỏ nhất.
3. Chưa đủ KPI ưu tiên — ``kpi_percent`` thấp nhất; ``None`` xem như thấp nhất
   (chưa có dữ liệu → ưu tiên nhận thêm).
4. Xoay vòng — ``last_assigned_at`` cũ nhất; ``None`` (chưa từng nhận) trước hết.

Trả ``user_id`` được chọn, hoặc ``None`` nếu không ứng viên nào trong ca.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from src.modules.assignment.domain.value_objects.candidate import AgentCandidate

# Mốc sớm nhất có thể, để ứng viên chưa từng được gán (last_assigned_at=None)
# luôn đứng trước theo round-robin.
_TRUOC_NHAT = datetime.min.replace(tzinfo=UTC)
# KPI khuyết xem như 0% (thấp nhất) → ưu tiên như người dưới target nhất.
_KPI_KHUYET = Decimal("-1")


def _khoa_xep_hang(c: AgentCandidate) -> tuple[int, Decimal, datetime, str]:
    """Khoá sắp xếp: nhỏ hơn = ưu tiên hơn. Chỉ gọi với ứng viên đã trong ca.

    (open_load ↑, kpi_percent ↑ với None thấp nhất, last_assigned_at ↑ với None
    sớm nhất, rồi ``user_id`` để phá hoà cuối cùng). Khoá ``user_id`` bảo đảm kết
    quả TẤT ĐỊNH kể cả khi mọi tiêu chí bằng nhau (ví dụ hệ thống mới, mọi ứng
    viên chưa từng nhận việc), không phụ thuộc thứ tự caller truyền vào.
    """
    kpi = c.kpi_percent if c.kpi_percent is not None else _KPI_KHUYET
    lan_gan_nhat = c.last_assigned_at if c.last_assigned_at is not None else _TRUOC_NHAT
    return (c.open_load, kpi, lan_gan_nhat, str(c.user_id))


def chon_nhan_vien(candidates: tuple[AgentCandidate, ...]) -> UUID | None:
    """Chọn một nhân viên theo chuỗi tiêu chí, hoặc ``None`` nếu không ai trong ca."""
    trong_ca = [c for c in candidates if c.on_shift]
    if not trong_ca:
        return None
    return min(trong_ca, key=_khoa_xep_hang).user_id
