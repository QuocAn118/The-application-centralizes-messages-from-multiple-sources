"""Domain service: phần trăm hoàn thành KPI tính theo *chiều* của chỉ số.

Tách khỏi use case ``GetKpiProgress`` để dùng chung: cả báo cáo tiến độ KPI của #4
lẫn định tuyến của #3 (pool ưu tiên người dưới target) đều cần đúng một công thức
này — không nhân bản logic chiều chỉ số ở hai nơi.
"""

from decimal import Decimal

from src.modules.hrm.domain.value_objects.kpi import KpiMetricType

# Các chỉ số mà "càng thấp càng tốt" — đạt mục tiêu là thực đạt <= mục tiêu.
# Mọi chỉ số khác mặc định "càng cao càng tốt" (thực đạt >= mục tiêu).
_METRIC_THAP_LA_TOT: frozenset[KpiMetricType] = frozenset({KpiMetricType.AVG_RESPONSE_MINUTES})


def tinh_phan_tram_kpi(
    metric_type: KpiMetricType, target: Decimal, actual: Decimal | None
) -> Decimal | None:
    """Phần trăm hoàn thành, tính theo *chiều* của chỉ số.

    - Chỉ số càng-cao-càng-tốt (mặc định): ``actual / target * 100``.
    - Chỉ số càng-thấp-càng-tốt (thời gian phản hồi): ``target / actual * 100`` —
      trả lời nhanh hơn mục tiêu cho ra > 100%, chậm hơn cho ra < 100%.

    Trả ``None`` khi chưa có thực đạt hoặc mẫu số bằng 0 (không xác định được).
    """
    if actual is None:
        return None

    if metric_type in _METRIC_THAP_LA_TOT:
        if actual == 0:
            return None
        return (target / actual * 100).quantize(Decimal("0.1"))

    if target == 0:
        return None
    return (actual / target * 100).quantize(Decimal("0.1"))
