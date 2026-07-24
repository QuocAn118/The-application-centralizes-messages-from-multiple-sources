"""Cấu hình log dạng JSON kèm mã định danh request."""

import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger.json import JsonFormatter

# Mã định danh request, gắn theo từng luồng xử lý bất đồng bộ để mọi dòng log
# của cùng một request đều truy vết được với nhau.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class _BoLocRequestId(logging.Filter):
    """Gắn ``request_id`` vào mọi bản ghi log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def cau_hinh_logging(log_level: str = "INFO") -> None:
    """Cấu hình log gốc.

    Xuất JSON để hệ thống thu thập log phân tích được, thay vì phải viết biểu
    thức chính quy trên chuỗi tự do.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
            rename_fields={"asctime": "thoi_diem", "levelname": "muc_do"},
        )
    )
    handler.addFilter(_BoLocRequestId())

    goc = logging.getLogger()
    goc.handlers.clear()
    goc.addHandler(handler)
    goc.setLevel(log_level.upper())
