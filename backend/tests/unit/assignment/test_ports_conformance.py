"""Xác nhận fake khớp đúng hợp đồng port của assignment.

Nếu một port đổi chữ ký mà fake không theo, phép gán dưới đây làm mypy đỏ.
"""

from src.modules.assignment.domain.ports import (
    IAgentPool,
    IConversationAssigner,
    IWaitingQueue,
)
from tests.unit.assignment.fakes import (
    FakeAgentPool,
    FakeConversationAssigner,
    FakeWaitingQueue,
)


def test_fake_khop_hop_dong_port() -> None:
    _pool: IAgentPool = FakeAgentPool()
    _assigner: IConversationAssigner = FakeConversationAssigner()
    _queue: IWaitingQueue = FakeWaitingQueue()
    assert all(obj is not None for obj in (_pool, _assigner, _queue))
