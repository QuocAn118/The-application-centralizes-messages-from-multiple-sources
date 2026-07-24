"""Port cho các phụ thuộc bên ngoài mà tầng application cần."""

from datetime import datetime
from typing import Protocol


class IClock(Protocol):
    """Nguồn thời gian.

    Tách thành port để test kiểm soát được thời gian mà không cần chờ đợi
    hay giả lập đồng hồ hệ thống.
    """

    def now(self) -> datetime:
        """Trả về thời điểm hiện tại theo UTC, luôn kèm thông tin timezone."""
        ...


class ITransaction(Protocol):
    """Điểm chốt giao dịch mà use case có thể tự commit khi cần.

    Quy ước chung là router mở giao dịch và commit sau khi use case chạy xong
    — nhờ đó nhiều thao tác gộp vào một giao dịch. Nhưng có một ngoại lệ: khi
    phát hiện refresh token bị đánh cắp, việc thu hồi cả chuỗi phải được ghi
    **dù request kết thúc bằng lỗi**. Nếu để nguyên, lớp xử lý HTTP sẽ rollback
    theo lỗi và xoá luôn hành động thu hồi, khiến kẻ tấn công vẫn dùng được
    token. Use case chốt giao dịch qua port này ngay trước khi ném lỗi.
    """

    async def commit(self) -> None:
        """Ghi vĩnh viễn các thay đổi đang chờ trong giao dịch hiện tại."""
        ...
