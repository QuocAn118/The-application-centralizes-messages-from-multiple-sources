"""Cấu hình log dạng JSON kèm mã định danh request."""

import logging
import re
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


_TOKEN_TRONG_URL = re.compile(r"(token=)[^&\s\"']+")


def che_token(chu: str) -> str:
    """Thay giá trị ``token=`` trong URL bằng ``***``."""
    return _TOKEN_TRONG_URL.sub(r"\1***", chu)


class _BoLocCheToken(logging.Filter):
    """Che access token trong URL trước khi uvicorn ghi log.

    WebSocket ``/ws/inbox?token=<access_token>`` mang token trên query string, và
    uvicorn ghi nguyên đường dẫn (``uvicorn.error`` lúc bắt tay, ``uvicorn.access``
    khi từ chối) — ai đọc được log là dùng được phiên đó tới khi token hết hạn.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = che_token(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(che_token(a) if isinstance(a, str) else a for a in record.args)
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

    # Lọc gắn vào LOGGER (không phải handler) vì uvicorn thay handler của chính nó
    # khi dựng cấu hình log, còn filter của logger thì giữ nguyên.
    for ten in ("uvicorn.access", "uvicorn.error"):
        lg = logging.getLogger(ten)
        if not any(isinstance(f, _BoLocCheToken) for f in lg.filters):
            lg.addFilter(_BoLocCheToken())
