"""Value object cho đơn từ nội bộ: loại đơn và trạng thái phê duyệt."""

from enum import StrEnum


class RequestType(StrEnum):
    """Loại biểu mẫu đơn từ nội bộ.

    Cố định (không có form builder động ở #4). Chỉ ``NGHI_PHEP`` bắt buộc có
    khoảng thời gian; các loại khác chỉ cần lý do text. Thêm loại mới là thêm
    một giá trị ở đây kèm luật validate tương ứng, không phải cấu hình runtime.
    """

    NGHI_PHEP = "NGHI_PHEP"
    TANG_LUONG = "TANG_LUONG"
    KHAC = "KHAC"


class RequestStatus(StrEnum):
    """Trạng thái vòng đời một đơn từ.

    ``CHO_DUYET``: vừa gửi, chờ người duyệt xử lý.
    ``DA_DUYET`` / ``TU_CHOI``: quyết định cuối — bất biến, không sửa lại.
    ``DA_HUY``: người gửi tự thu hồi khi chưa ai duyệt.
    """

    CHO_DUYET = "CHO_DUYET"
    DA_DUYET = "DA_DUYET"
    TU_CHOI = "TU_CHOI"
    DA_HUY = "DA_HUY"
