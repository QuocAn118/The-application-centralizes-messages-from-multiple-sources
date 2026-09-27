"""#2 tự phân phòng và #3 tự giao việc: tín hiệu realtime chỉ phát SAU commit.

Hook chạy trên session riêng; phát giữa transaction thì client đọc lại REST thấy
dữ liệu cũ. Session được bind vào một transaction ngoài (commit của session chỉ nhả
savepoint) để kiểm được đường commit mà không để lại dữ liệu trong DB test.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.modules.assignment.infrastructure.inbox_bridge.conversation_assigner import (
    InboxConversationAssigner,
)
from src.modules.assignment.infrastructure.persistence.assignment_log_repository import (
    SqlAlchemyAssignmentLog,
)
from src.modules.inbox.domain.entities.conversation import ConversationStatus
from src.modules.keyword.infrastructure.inbox_bridge.conversation_router import (
    InboxConversationRouter,
)
from src.shared.infrastructure.clock import SystemClock
from tests.integration.test_assignment_bridges import NOW, _Clock, _hoi_thoai, _nhan_vien
from tests.integration.test_assignment_bridges import _phong as _phong_3
from tests.integration.test_keyword_repositories import _hoi_thoai_cho_phan
from tests.integration.test_keyword_repositories import _phong as _phong_2
from tests.unit.inbox.fakes import FakeRealtimeNotifier

pytestmark = pytest.mark.integration


@pytest.fixture
async def s(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as conn:
        ngoai = await conn.begin()
        async with AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        ) as session:
            yield session
        await ngoai.rollback()


async def test_3_tu_giao_viec_phat_sau_commit(s: AsyncSession) -> None:
    phong = await _phong_3(s)
    nv = await _nhan_vien(s, phong.id)
    conv = await _hoi_thoai(
        s, phong.id, assigned_user_id=None, status=ConversationStatus.DANG_MO, last_message_at=NOW
    )
    tb = FakeRealtimeNotifier()
    await InboxConversationAssigner(s, tb, _Clock(), SqlAlchemyAssignmentLog(s)).assign_to_agent(
        conv.id, nv.id, phong.id
    )
    assert tb.signals == [] and tb.rieng == []  # chưa commit → chưa ai được báo

    await s.commit()
    await asyncio.sleep(0.05)
    assert [x[0] for x in tb.signals] == [conv.id]
    assert [x[0] for x in tb.rieng] == [nv.id]


async def test_2_tu_phan_phong_phat_sau_commit(s: AsyncSession) -> None:
    conv = await _hoi_thoai_cho_phan(s)
    phong = await _phong_2(s)
    tb = FakeRealtimeNotifier()
    assert await InboxConversationRouter(s, notifier=tb, clock=SystemClock()).assign_to_department(
        conv.id, phong.id
    )
    assert tb.signals == []

    await s.commit()
    await asyncio.sleep(0.05)
    assert [x[0] for x in tb.signals] == [conv.id]
