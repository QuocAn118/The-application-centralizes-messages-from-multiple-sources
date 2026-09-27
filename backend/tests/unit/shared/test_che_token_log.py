"""Access token trên URL WebSocket không được lọt vào log của uvicorn."""

import logging

import pytest

from src.shared.infrastructure.logging import cau_hinh_logging

TOKEN = "eyJhbGciOi.eyJzdWIiOi.chu-ky_bi-mat"


@pytest.fixture
def log_goc(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    cau_hinh_logging("INFO")
    # cau_hinh_logging thay handler gốc -> gắn lại handler của caplog.
    logging.getLogger().addHandler(caplog.handler)
    return caplog


def test_ban_tay_websocket_tren_uvicorn_error(log_goc: pytest.LogCaptureFixture) -> None:
    # Đúng chuỗi định dạng uvicorn dùng khi chấp nhận kết nối WebSocket.
    logging.getLogger("uvicorn.error").info(
        '%s - "WebSocket %s" [accepted]', "127.0.0.1:5000", f"/ws/inbox?token={TOKEN}"
    )
    assert TOKEN not in log_goc.text
    assert "/ws/inbox?token=***" in log_goc.text


def test_dong_access_log(log_goc: pytest.LogCaptureFixture) -> None:
    # Đúng bộ tham số của uvicorn.access: client, method, path, http version, status.
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d',
        "127.0.0.1:5000",
        "GET",
        f"/ws/inbox?a=1&token={TOKEN}&b=2",
        "1.1",
        403,
    )
    assert TOKEN not in log_goc.text
    assert "a=1&token=***&b=2" in log_goc.text


def test_goi_nhieu_lan_khong_nhan_doi_bo_loc() -> None:
    cau_hinh_logging("INFO")
    cau_hinh_logging("INFO")
    assert len(logging.getLogger("uvicorn.error").filters) == 1
