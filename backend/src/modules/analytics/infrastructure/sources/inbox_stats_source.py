"""Cầu nối analytics → #1 (đọc): quét bảng nguồn để backfill rollup một ngày.

Implementation ``IConversationStatsSource``. Áp dụng **quy tắc event-time** (chốt
review GĐ2): mỗi số liệu gắn ngày của hành động sinh ra nó, quy đổi ``timezone``
(``app_timezone``) rồi lấy ``::date`` trên timestamp của TỪNG bản ghi — KHÔNG group
theo ngày mở hội thoại — để khớp incremental.

Ranh giới chính xác của backfill (nguồn #1 không lưu nhật ký sự kiện):
- **inbound/outbound**: CHÍNH XÁC — đếm từ ``messages`` theo ``created_at`` của tin.
- **opened**: đếm hội thoại có phòng theo ``created_at`` (proxy: mở ≈ tạo).
- **closed/handled/resolution**: dùng ``updated_at`` của hội thoại ``DA_DONG`` làm
  mốc đóng (proxy thô như #3; với hội thoại đã đóng, lần cập nhật cuối thường là
  lúc đóng). ``resolution`` = ``updated_at - created_at`` (giây).
- **first_response**: giây từ tin INBOUND đầu tới tin OUTBOUND đầu của mỗi hội
  thoại, gắn ngày của tin OUTBOUND đầu.

NỢ (ghi ở plan): incremental có mốc đóng chính xác (thời điểm hook) còn backfill
xấp xỉ bằng ``updated_at`` → có thể lệch nhẹ ở closed/resolution. ``assigned_count``
KHÔNG dựng lại từ backfill (thiếu ``assignment_log`` #3) — chỉ incremental cộng khi
có sự kiện ASSIGNED.
"""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from src.modules.analytics.domain.value_objects.metrics import (
    DailyAgentMetric,
    DailyConversationMetric,
)
from src.modules.inbox.infrastructure.models.channel_model import ChannelModel
from src.modules.inbox.infrastructure.models.conversation_model import ConversationModel
from src.modules.inbox.infrastructure.models.message_model import MessageModel


class InboxStatsSource:
    """Quét #1 dựng lại rollup một ngày theo giờ địa phương (event-time)."""

    def __init__(self, session: AsyncSession, timezone: str) -> None:
        self._session = session
        self._tz = timezone

    def _ngay_local(self, cot: Any) -> ColumnElement[date]:
        """Ngày nghiệp vụ địa phương của một ``timestamptz``: đổi tz rồi ``::date``.

        ``timezone(tz, ts_tz)`` cho ``timestamp`` giờ tường (local); ``date(...)``
        lấy ngày — đúng quy tắc event-time. ``cot`` là một biểu thức cột datetime
        (cột model hoặc cột subquery) nên nhận ``Any`` cho gọn kiểu.
        """
        result: ColumnElement[date] = func.date(func.timezone(self._tz, cot))
        return result

    async def conversation_metrics_cho_ngay(
        self, work_date: date
    ) -> tuple[DailyConversationMetric, ...]:
        rows: dict[tuple[UUID | None, str], dict[str, int]] = {}

        # inbound/outbound theo tin: message → conversation → channel, lọc ngày tin.
        cau_tin = (
            select(
                ConversationModel.department_id.label("dept"),
                ChannelModel.platform.label("platform"),
                func.count().filter(MessageModel.direction == "INBOUND").label("inbound"),
                func.count().filter(MessageModel.direction == "OUTBOUND").label("outbound"),
            )
            .select_from(MessageModel)
            .join(ConversationModel, ConversationModel.id == MessageModel.conversation_id)
            .join(ChannelModel, ChannelModel.id == ConversationModel.channel_id)
            .where(self._ngay_local(MessageModel.created_at) == work_date)
            .group_by(ConversationModel.department_id, ChannelModel.platform)
        )
        for r in await self._session.execute(cau_tin):
            o = rows.setdefault(
                (r.dept, r.platform),
                {"inbound": 0, "outbound": 0, "opened": 0, "closed": 0},
            )
            o["inbound"] += r.inbound
            o["outbound"] += r.outbound

        # opened: hội thoại có phòng, theo ngày tạo (proxy mở ≈ tạo).
        cau_mo = (
            select(
                ConversationModel.department_id.label("dept"),
                ChannelModel.platform.label("platform"),
                func.count().label("opened"),
            )
            .select_from(ConversationModel)
            .join(ChannelModel, ChannelModel.id == ConversationModel.channel_id)
            .where(
                self._ngay_local(ConversationModel.created_at) == work_date,
                ConversationModel.department_id.isnot(None),
            )
            .group_by(ConversationModel.department_id, ChannelModel.platform)
        )
        for r_mo in await self._session.execute(cau_mo):
            o = rows.setdefault(
                (r_mo.dept, r_mo.platform),
                {"inbound": 0, "outbound": 0, "opened": 0, "closed": 0},
            )
            o["opened"] += r_mo.opened

        # closed: hội thoại DA_DONG, theo ngày updated_at (proxy mốc đóng).
        cau_dong = (
            select(
                ConversationModel.department_id.label("dept"),
                ChannelModel.platform.label("platform"),
                func.count().label("closed"),
            )
            .select_from(ConversationModel)
            .join(ChannelModel, ChannelModel.id == ConversationModel.channel_id)
            .where(
                self._ngay_local(ConversationModel.updated_at) == work_date,
                ConversationModel.status == "DA_DONG",
            )
            .group_by(ConversationModel.department_id, ChannelModel.platform)
        )
        for r_dong in await self._session.execute(cau_dong):
            o = rows.setdefault(
                (r_dong.dept, r_dong.platform),
                {"inbound": 0, "outbound": 0, "opened": 0, "closed": 0},
            )
            o["closed"] += r_dong.closed

        return tuple(
            DailyConversationMetric(
                work_date=work_date,
                department_id=dept,
                channel_platform=platform,
                inbound_count=v["inbound"],
                outbound_count=v["outbound"],
                opened_count=v["opened"],
                closed_count=v["closed"],
            )
            for (dept, platform), v in rows.items()
        )

    async def agent_metrics_cho_ngay(self, work_date: date) -> tuple[DailyAgentMetric, ...]:
        acc: dict[tuple[UUID, UUID | None], dict[str, int]] = {}

        def _o(user_id: UUID, dept: UUID | None) -> dict[str, int]:
            return acc.setdefault(
                (user_id, dept),
                {"handled": 0, "res_sum": 0, "res_n": 0, "fr_sum": 0, "fr_n": 0},
            )

        # handled + resolution: hội thoại DA_DONG có người nhận, mốc đóng =
        # updated_at (proxy), gắn ngày updated_at local.
        giay_xu_ly = cast(
            func.extract("epoch", ConversationModel.updated_at)
            - func.extract("epoch", ConversationModel.created_at),
            Integer,
        )
        cau_dong = select(
            ConversationModel.assigned_user_id.label("uid"),
            ConversationModel.department_id.label("dept"),
            giay_xu_ly.label("giay"),
        ).where(
            self._ngay_local(ConversationModel.updated_at) == work_date,
            ConversationModel.status == "DA_DONG",
            ConversationModel.assigned_user_id.isnot(None),
        )
        for r_dong in await self._session.execute(cau_dong):
            o = _o(r_dong.uid, r_dong.dept)
            o["handled"] += 1
            if r_dong.giay is not None and r_dong.giay >= 0:
                o["res_sum"] += int(r_dong.giay)
                o["res_n"] += 1

        # first_response: mỗi hội thoại, giây từ tin INBOUND đầu tới OUTBOUND đầu,
        # gắn ngày của tin OUTBOUND đầu. Mốc đầu mỗi chiều = min(created_at). Người
        # gửi tin OUTBOUND đầu: array_agg theo created_at rồi lấy phần tử [1]
        # (Postgres không có min(uuid); cần đúng "người của tin đầu", không phải
        # UUID nhỏ nhất).
        m_in = func.min(MessageModel.created_at).filter(MessageModel.direction == "INBOUND")
        m_out = func.min(MessageModel.created_at).filter(MessageModel.direction == "OUTBOUND")
        out_user = func.array_agg(
            aggregate_order_by(MessageModel.sender_user_id, MessageModel.created_at)
        ).filter(MessageModel.direction == "OUTBOUND")[1]
        sub = (
            select(
                MessageModel.conversation_id.label("cid"),
                m_in.label("in_dau"),
                m_out.label("out_dau"),
                out_user.label("out_user"),
            )
            .group_by(MessageModel.conversation_id)
            .subquery()
        )
        cau_fr = (
            select(
                sub.c.out_user.label("uid"),
                ConversationModel.department_id.label("dept"),
                cast(
                    func.extract("epoch", sub.c.out_dau) - func.extract("epoch", sub.c.in_dau),
                    Integer,
                ).label("giay"),
            )
            .select_from(sub)
            .join(ConversationModel, ConversationModel.id == sub.c.cid)
            .where(
                sub.c.in_dau.isnot(None),
                sub.c.out_dau.isnot(None),
                sub.c.out_user.isnot(None),
                self._ngay_local(sub.c.out_dau) == work_date,
            )
        )
        for r_fr in await self._session.execute(cau_fr):
            if r_fr.giay is None or r_fr.giay < 0:
                continue
            o = _o(r_fr.uid, r_fr.dept)
            o["fr_sum"] += int(r_fr.giay)
            o["fr_n"] += 1

        return tuple(
            DailyAgentMetric(
                work_date=work_date,
                user_id=uid,
                department_id=dept,
                handled_count=v["handled"],
                assigned_count=0,  # backfill không dựng assigned (thiếu assignment_log)
                sum_first_response_seconds=v["fr_sum"],
                first_response_samples=v["fr_n"],
                sum_resolution_seconds=v["res_sum"],
                resolution_samples=v["res_n"],
            )
            for (uid, dept), v in acc.items()
        )
