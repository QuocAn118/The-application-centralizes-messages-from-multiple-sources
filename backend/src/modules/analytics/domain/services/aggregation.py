"""Gộp số liệu — logic thuần, không I/O.

Hai việc chính:
- Gộp nhiều dòng rollup ngày (nhiều ngày, cùng một nhân viên/phòng) thành một số
  liệu trình bày duy nhất cho khoảng báo cáo.
- Tính trung bình từ **tổng + số mẫu** (``sum/samples``) — cộng dồn nhiều ngày rồi
  mới chia, nên trung bình đúng dù mỗi ngày có số mẫu khác nhau; ``samples == 0``
  trả ``None`` (không có dữ liệu, KHÁC 0).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from src.modules.analytics.domain.value_objects.metrics import (
    AgentPerformance,
    ConversationVolume,
    DailyAgentMetric,
    DailyConversationMetric,
)


@dataclass
class _TichLuyNhanVien:
    """Bộ cộng dồn tạm cho một nhân viên khi gộp nhiều ngày (nội bộ)."""

    handled: int = 0
    assigned: int = 0
    fr_sum: int = 0
    fr_n: int = 0
    res_sum: int = 0
    res_n: int = 0

    def cong(self, m: DailyAgentMetric) -> None:
        self.handled += m.handled_count
        self.assigned += m.assigned_count
        self.fr_sum += m.sum_first_response_seconds
        self.fr_n += m.first_response_samples
        self.res_sum += m.sum_resolution_seconds
        self.res_n += m.resolution_samples


def trung_binh(tong: int, so_mau: int) -> float | None:
    """Trung bình từ tổng + số mẫu; ``None`` khi chưa có mẫu nào.

    Trả ``None`` (không phải 0) khi ``so_mau == 0`` để phân biệt "không có dữ
    liệu" với "trung bình bằng 0".
    """
    if so_mau <= 0:
        return None
    return tong / so_mau


def gop_khoi_luong(metrics: Iterable[DailyConversationMetric]) -> ConversationVolume:
    """Cộng dồn nhiều dòng khối lượng thành một tổng cho khoảng báo cáo."""
    inbound = outbound = opened = closed = 0
    for m in metrics:
        inbound += m.inbound_count
        outbound += m.outbound_count
        opened += m.opened_count
        closed += m.closed_count
    return ConversationVolume(
        inbound_count=inbound,
        outbound_count=outbound,
        opened_count=opened,
        closed_count=closed,
    )


def gop_hieu_suat_nhan_vien(
    metrics: Iterable[DailyAgentMetric],
) -> tuple[AgentPerformance, ...]:
    """Gộp các dòng ngày theo ``user_id`` → một ``AgentPerformance`` mỗi người.

    Cộng dồn tổng giây + số mẫu qua các ngày rồi mới tính trung bình (đúng khi
    mỗi ngày số mẫu khác nhau). Giữ thứ tự xuất hiện đầu tiên của mỗi nhân viên
    để kết quả tất định.
    """
    thu_tu: list[UUID] = []
    gom: dict[UUID, _TichLuyNhanVien] = {}
    for m in metrics:
        acc = gom.get(m.user_id)
        if acc is None:
            acc = _TichLuyNhanVien()
            gom[m.user_id] = acc
            thu_tu.append(m.user_id)
        acc.cong(m)

    ket_qua: list[AgentPerformance] = []
    for user_id in thu_tu:
        a = gom[user_id]
        ket_qua.append(
            AgentPerformance(
                user_id=user_id,
                handled_count=a.handled,
                assigned_count=a.assigned,
                avg_first_response_seconds=trung_binh(a.fr_sum, a.fr_n),
                avg_resolution_seconds=trung_binh(a.res_sum, a.res_n),
            )
        )
    return tuple(ket_qua)
