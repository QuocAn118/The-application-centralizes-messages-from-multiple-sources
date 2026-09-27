"""Chốt chặn của script dev ``don_ca_thu``: không bao giờ chạy trên production."""

import pytest

from scripts.don_ca_thu import ly_do_tu_choi

DEV = "postgresql+asyncpg://postgres:postgres@localhost:5432/omnichat"


def test_dev_localhost_thi_cho_chay() -> None:
    assert ly_do_tu_choi("development", DEV) is None
    assert ly_do_tu_choi("development", DEV.replace("localhost", "127.0.0.1")) is None


@pytest.mark.parametrize("env", ["production", "PRODUCTION", " prod "])
def test_production_thi_tu_choi_du_db_cuc_bo(env: str) -> None:
    assert ly_do_tu_choi(env, DEV) is not None


def test_db_khong_o_localhost_thi_tu_choi() -> None:
    assert ly_do_tu_choi("development", DEV.replace("localhost", "db.congty.vn")) is not None
