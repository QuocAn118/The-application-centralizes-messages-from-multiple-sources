"""Kiểm tra schema thật của các bảng inbox trong PostgreSQL.

Các ràng buộc quan trọng nhất (idempotency webhook, unique kênh, CASCADE) nằm ở
tầng DB; test này xác nhận chúng thực sự có hiệu lực, không chỉ khai báo Python.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)


async def _them_kenh(
    session: AsyncSession,
    platform: str = "ZALO",
    external: str = "oa_1",
    department_id: str | None = None,
) -> str:
    ket_qua = await session.execute(
        text(
            "INSERT INTO channels (id, platform, external_channel_id, name, credential, "
            "department_id, is_active, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :pf, :ext, 'OA', 'enc::x', :dept, true, :bg, :bg) "
            "RETURNING id"
        ),
        {"pf": platform, "ext": external, "dept": department_id, "bg": BAY_GIO},
    )
    return str(ket_qua.scalar_one())


async def _them_khach(session: AsyncSession, channel_id: str, external: str = "cust_1") -> str:
    ket_qua = await session.execute(
        text(
            "INSERT INTO customers (id, channel_id, platform, external_id, display_name, "
            "avatar_url, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :ch, 'ZALO', :ext, 'Khach', NULL, :bg, :bg) RETURNING id"
        ),
        {"ch": channel_id, "ext": external, "bg": BAY_GIO},
    )
    return str(ket_qua.scalar_one())


async def _them_hoi_thoai(session: AsyncSession, channel_id: str, customer_id: str) -> str:
    ket_qua = await session.execute(
        text(
            "INSERT INTO conversations (id, channel_id, customer_id, status, department_id, "
            "assigned_user_id, last_message_at, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :ch, :cu, 'DANG_MO', NULL, NULL, :bg, :bg, :bg) "
            "RETURNING id"
        ),
        {"ch": channel_id, "cu": customer_id, "bg": BAY_GIO},
    )
    return str(ket_qua.scalar_one())


async def _them_tin(
    session: AsyncSession,
    conversation_id: str,
    external_message_id: str | None,
    direction: str = "INBOUND",
) -> str:
    ket_qua = await session.execute(
        text(
            "INSERT INTO messages (id, conversation_id, direction, text, external_message_id, "
            "sender_user_id, created_at) "
            "VALUES (gen_random_uuid(), :cv, :dir, 'hi', :ext, NULL, :bg) RETURNING id"
        ),
        {"cv": conversation_id, "dir": direction, "ext": external_message_id, "bg": BAY_GIO},
    )
    return str(ket_qua.scalar_one())


class TestKenhUnique:
    async def test_kenh_trung_platform_external_bi_chan(self, db_session: AsyncSession) -> None:
        await _them_kenh(db_session, "ZALO", "oa_dup")
        await db_session.flush()

        with pytest.raises(IntegrityError):
            await _them_kenh(db_session, "ZALO", "oa_dup")
            await db_session.flush()

    async def test_cung_external_khac_platform_van_duoc(self, db_session: AsyncSession) -> None:
        await _them_kenh(db_session, "ZALO", "same_id")
        await _them_kenh(db_session, "FACEBOOK", "same_id")
        await db_session.flush()  # không lỗi

    async def test_platform_la_bi_chan(self, db_session: AsyncSession) -> None:
        with pytest.raises(IntegrityError):
            await _them_kenh(db_session, "TIKTOK", "x")
            await db_session.flush()


class TestKhachUnique:
    async def test_khach_trung_kenh_external_bi_chan(self, db_session: AsyncSession) -> None:
        ch = await _them_kenh(db_session)
        await _them_khach(db_session, ch, "c_dup")
        await db_session.flush()

        with pytest.raises(IntegrityError):
            await _them_khach(db_session, ch, "c_dup")
            await db_session.flush()


class TestIdempotencyIndex:
    async def test_external_message_id_trung_bi_chan(self, db_session: AsyncSession) -> None:
        ch = await _them_kenh(db_session)
        cu = await _them_khach(db_session, ch)
        cv = await _them_hoi_thoai(db_session, ch, cu)
        await _them_tin(db_session, cv, "msg_dup")
        await db_session.flush()

        with pytest.raises(IntegrityError):
            await _them_tin(db_session, cv, "msg_dup")
            await db_session.flush()

    async def test_nhieu_tin_di_external_null_khong_dung_rang_buoc(
        self, db_session: AsyncSession
    ) -> None:
        ch = await _them_kenh(db_session)
        cu = await _them_khach(db_session, ch)
        cv = await _them_hoi_thoai(db_session, ch, cu)
        # Partial index chỉ áp khi external_message_id IS NOT NULL: nhiều tin đi
        # (NULL) không được coi là trùng.
        await _them_tin(db_session, cv, None, direction="OUTBOUND")
        await _them_tin(db_session, cv, None, direction="OUTBOUND")
        await db_session.flush()  # không lỗi


class TestCheckVaCascade:
    async def test_status_la_bi_chan(self, db_session: AsyncSession) -> None:
        ch = await _them_kenh(db_session)
        cu = await _them_khach(db_session, ch)
        with pytest.raises(IntegrityError):
            await db_session.execute(
                text(
                    "INSERT INTO conversations (id, channel_id, customer_id, status, "
                    "department_id, assigned_user_id, last_message_at, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), :ch, :cu, 'XYZ', NULL, NULL, :bg, :bg, :bg)"
                ),
                {"ch": ch, "cu": cu, "bg": BAY_GIO},
            )
            await db_session.flush()

    async def test_xoa_kenh_cascade_xuong_khach_hoi_thoai_tin(
        self, db_session: AsyncSession
    ) -> None:
        ch = await _them_kenh(db_session)
        cu = await _them_khach(db_session, ch)
        cv = await _them_hoi_thoai(db_session, ch, cu)
        await _them_tin(db_session, cv, "m1")
        await db_session.flush()

        await db_session.execute(text("DELETE FROM channels WHERE id = :id"), {"id": ch})
        await db_session.flush()

        con_lai = await db_session.execute(
            text("SELECT count(*) FROM messages WHERE conversation_id = :cv"), {"cv": cv}
        )
        assert con_lai.scalar_one() == 0
