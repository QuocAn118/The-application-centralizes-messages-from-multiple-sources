"""Đo RIÊNG phần Phần 2a thêm vào `GET /inbox`, trên DB omnichat_perf.

Vì sao không đo qua HTTP: trên máy dev số đo HTTP dao động rất mạnh (nhiều tiến
trình chạy cùng), không tách được phần chi phí mới khỏi nhiễu. Ở đây gọi thẳng
đúng các hàm repository mà use case gọi, cho trang đầu (25 hội thoại) của từng vai,
và in kèm chi phí truy vấn danh sách cũ để có thang so.

    uv run python -m scripts.perf.giai_thich [--lan 50]
"""

import argparse
import statistics
import sys
import time
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.identity.infrastructure.models.user_model import UserModel
from src.modules.inbox.application.actor import ActorRole, InboxActor
from src.modules.inbox.application.use_cases.list_inbox import pham_vi_cua
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.inbox.infrastructure.repositories.message_repository import (
    SqlAlchemyMessageRepository,
)
from src.shared.infrastructure.event_loop import chay_async

URL = "postgresql+psycopg://postgres@localhost:5432/omnichat_perf"
EMAIL = {
    "ADMIN": "perf.admin@congty.vn",
    "MANAGER": "perf.mgr0@congty.vn",
    "STAFF": "perf.staff0@congty.vn",
}


async def do(ham: Callable[[], Awaitable[Any]], lan: int) -> tuple[float, float]:
    await ham()  # làm nóng
    ms = []
    for _ in range(lan):
        t0 = time.perf_counter()
        await ham()
        ms.append((time.perf_counter() - t0) * 1000)
    ms.sort()
    return statistics.median(ms), ms[max(0, int(len(ms) * 0.95) - 1)]


async def do_mot_vai(
    conv: SqlAlchemyConversationRepository,
    msg: SqlAlchemyMessageRepository,
    actor: InboxActor,
    lan: int,
) -> list[tuple[str, float, float]]:
    """Đo 4 truy vấn cho trang đầu của MỘT vai (tách hàm để closure không bám biến vòng lặp)."""
    pv = pham_vi_cua(actor)
    trang = await conv.list_for_scope(pv.department_ids, pv.include_awaiting, limit=25)
    ids = [c.id for c in trang]

    async def cu_list() -> None:
        await conv.list_for_scope(pv.department_ids, pv.include_awaiting, limit=25)
        await conv.count_for_scope(pv.department_ids, pv.include_awaiting)

    async def moi_chua_doc() -> None:
        await msg.unread_counts(actor.user_id, ids)

    async def moi_cho() -> None:
        await msg.waiting_since(ids)

    async def moi_huy_hieu() -> None:
        await conv.count_unread_for_scope(pv.department_ids, pv.include_awaiting, actor.user_id)

    ket_qua = []
    for ten, ham in (
        ("danh sach+dem (CU)", cu_list),
        ("unread_counts (MOI)", moi_chua_doc),
        ("waiting_since (MOI)", moi_cho),
        ("unread-count nav (MOI)", moi_huy_hieu),
    ):
        p50, p95 = await do(ham, lan)
        ket_qua.append((ten, p50, p95))
    return ket_qua


async def main(lan: int) -> None:
    engine = create_async_engine(URL)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as s:
        conv = SqlAlchemyConversationRepository(s)
        msg = SqlAlchemyMessageRepository(s)
        for vai, email in EMAIL.items():
            u = (await s.execute(select(UserModel).where(UserModel.email == email))).scalar_one()
            actor = InboxActor(user_id=u.id, role=ActorRole(vai), department_id=u.department_id)
            for ten, p50, p95 in await do_mot_vai(conv, msg, actor, lan):
                print(f"{vai:8} {ten:24} p50={p50:7.2f}ms  p95={p95:7.2f}ms")
    await engine.dispose()


if __name__ == "__main__":
    for luong in (sys.stdout,):
        if hasattr(luong, "reconfigure"):
            luong.reconfigure(encoding="utf-8", errors="replace")
    bo_doc = argparse.ArgumentParser()
    bo_doc.add_argument("--lan", type=int, default=50)
    chay_async(main(bo_doc.parse_args().lan))
