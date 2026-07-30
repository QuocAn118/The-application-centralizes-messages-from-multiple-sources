"""Test value object AgentCandidate — bất biến (frozen) + mặc định."""

from decimal import Decimal
from uuid import UUID

import pytest

from src.modules.assignment.domain.value_objects.candidate import (
    AgentCandidate,
    AssignmentOutcome,
)

U = UUID("00000000-0000-0000-0000-0000000000a1")


def test_mac_dinh_kpi_va_last_assigned_none() -> None:
    c = AgentCandidate(user_id=U, on_shift=True, open_load=0)
    assert c.kpi_percent is None
    assert c.last_assigned_at is None


def test_frozen_khong_sua_duoc() -> None:
    c = AgentCandidate(user_id=U, on_shift=True, open_load=1, kpi_percent=Decimal("50"))
    with pytest.raises(AttributeError):
        c.open_load = 2  # type: ignore[misc]


def test_outcome_gia_tri() -> None:
    assert {o.value for o in AssignmentOutcome} == {"ASSIGNED", "QUEUED", "SKIPPED"}
