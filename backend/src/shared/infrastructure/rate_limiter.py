"""Giới hạn tần suất gọi, lưu trong bộ nhớ tiến trình."""

from collections import defaultdict
from datetime import datetime, timedelta

from src.shared.application.exceptions import ApplicationError
from src.shared.application.ports import IClock


class RateLimitExceededError(ApplicationError):
    """Vượt quá số lần cho phép trong khoảng thời gian quy định."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            f"Bạn đã thử quá nhiều lần. Vui lòng thử lại sau "
            f"{retry_after_seconds} giây.",
            code="RATE_LIMIT_EXCEEDED",
        )
        self.retry_after_seconds = retry_after_seconds


class InMemoryRateLimiter:
    """Đếm số lần gọi theo cửa sổ trượt, giữ trong bộ nhớ.

    **Giới hạn quan trọng:** bộ đếm nằm trong bộ nhớ của một tiến trình. Khi
    chạy nhiều bản sao, mỗi bản giữ bộ đếm riêng nên ngưỡng thực tế bị nhân lên
    theo số bản sao. Với mục tiêu 1000 người dùng đồng thời, hệ thống gần như
    chắc chắn phải chạy nhiều bản sao — lúc đó cần chuyển bộ đếm sang Redis.
    Xem mục 9 của spec.
    """

    def __init__(
        self, max_attempts: int, window_seconds: int, clock: IClock
    ) -> None:
        self._max_attempts = max_attempts
        self._window = timedelta(seconds=window_seconds)
        self._clock = clock
        self._lan_goi: dict[str, list[datetime]] = defaultdict(list)

    def _don_rac(self, bay_gio: datetime) -> None:
        """Xoá các khoá không còn lần gọi nào trong cửa sổ.

        Không dọn thì mỗi email bị kẻ tấn công thử sẽ chiếm bộ nhớ vĩnh viễn.
        """
        moc = bay_gio - self._window
        khoa_can_xoa = [
            khoa
            for khoa, danh_sach in self._lan_goi.items()
            if not any(t > moc for t in danh_sach)
        ]
        for khoa in khoa_can_xoa:
            del self._lan_goi[khoa]

    def check(self, key: str) -> None:
        """Ghi nhận một lần gọi và chặn nếu vượt ngưỡng."""
        bay_gio = self._clock.now()
        self._don_rac(bay_gio)

        moc = bay_gio - self._window
        con_hieu_luc = [t for t in self._lan_goi[key] if t > moc]

        if len(con_hieu_luc) >= self._max_attempts:
            som_nhat = min(con_hieu_luc)
            con_lai = (som_nhat + self._window - bay_gio).total_seconds()
            # Làm tròn lên để không báo "thử lại sau 0 giây", nhưng kẹp trần ở
            # độ dài cửa sổ: thời gian chờ không bao giờ vượt quá nó.
            cho_them = min(int(con_lai) + 1, int(self._window.total_seconds()))
            self._lan_goi[key] = con_hieu_luc
            raise RateLimitExceededError(retry_after_seconds=max(cho_them, 1))

        con_hieu_luc.append(bay_gio)
        self._lan_goi[key] = con_hieu_luc

    def reset(self, key: str) -> None:
        """Xoá bộ đếm của một khoá, gọi sau khi đăng nhập thành công."""
        self._lan_goi.pop(key, None)

    def so_khoa_dang_giu(self) -> int:
        """Số khoá đang lưu — dùng để kiểm chứng việc dọn rác trong test."""
        return len(self._lan_goi)
