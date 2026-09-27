"""Tín hiệu realtime chỉ phát SAU commit (client đọc lại REST phải thấy dữ liệu mới)."""

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.inbox.infrastructure.realtime.sau_commit import NotifierSauCommit
from src.shared.domain.identifiers import new_id
from tests.unit.inbox.fakes import FakeRealtimeNotifier

pytestmark = pytest.mark.integration


async def test_giu_toi_khi_commit(session_factory: async_sessionmaker[AsyncSession]) -> None:
    goc = FakeRealtimeNotifier()
    async with session_factory() as s:
        n = NotifierSauCommit(goc, s)
        ht, nguoi = new_id(), new_id()
        await n.notify_conversation_changed(ht, None, "status_changed")
        await n.notify_user(nguoi, ht, "assigned_to_you")
        await s.execute(text("select 1"))
        assert goc.signals == [] and goc.rieng == []

        await s.commit()
        await asyncio.sleep(0.05)
        assert goc.signals == [(ht, None, "status_changed")]
        assert goc.rieng == [(nguoi, ht, "assigned_to_you")]


async def test_rollback_thi_bo(session_factory: async_sessionmaker[AsyncSession]) -> None:
    goc = FakeRealtimeNotifier()
    async with session_factory() as s:
        n = NotifierSauCommit(goc, s)
        await n.notify_conversation_changed(new_id(), None, "status_changed")
        await s.execute(text("select 1"))
        await s.rollback()
        await s.commit()  # commit sau đó không được phát lại tín hiệu đã bỏ
        await asyncio.sleep(0.05)
        assert goc.signals == []
