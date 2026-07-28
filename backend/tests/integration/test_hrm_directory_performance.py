"""Integration test cho hai cầu nối của hrm sang module khác:

- IdentityWorkforceDirectory: đọc nhân viên/Manager từ identity.
- InboxPerformanceSource: tính KPI thực đạt từ hội thoại inbox.

Cả hai là chỗ DUY NHẤT hrm chạm identity/inbox; test seed dữ liệu thật của hai
module đó rồi xác nhận hrm đọc/tính đúng.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.hrm.domain.value_objects.kpi import KpiMetricType, KpiPeriod
from src.modules.hrm.infrastructure.directory.workforce_directory import (
    IdentityWorkforceDirectory,
)
from src.modules.hrm.infrastructure.performance.inbox_performance_source import (
    InboxPerformanceSource,
)
from src.modules.identity.domain.entities.department import Department
from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.email import Email
from src.modules.identity.domain.value_objects.password_hash import PasswordHash
from src.modules.identity.domain.value_objects.role import Role
from src.modules.identity.infrastructure.repositories.department_repository import (
    SqlAlchemyDepartmentRepository,
)
from src.modules.identity.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.shared.domain.identifiers import new_id

pytestmark = pytest.mark.integration

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
KY = KpiPeriod(year=2026, month=8)
_HASH = PasswordHash("$2b$12$" + "a" * 53)


async def _phong(session: AsyncSession, ten: str) -> Department:
    repo = SqlAlchemyDepartmentRepository(session)
    p = Department.create(name=ten, description=None, now=BAY_GIO)
    await repo.add(p)
    await session.flush()
    return p


async def _nhan_vien(session: AsyncSession, department_id, role: Role = Role.STAFF) -> User:
    repo = SqlAlchemyUserRepository(session)
    u = User.create(
        email=Email(f"{new_id().hex}@x.vn"),
        password_hash=_HASH,
        full_name="NV",
        role=role,
        department_id=department_id,
        now=BAY_GIO,
    )
    await repo.add(u)
    await session.flush()
    return u


class TestWorkforceDirectory:
    async def test_get_manager_of_department(self, db_session: AsyncSession) -> None:
        directory = IdentityWorkforceDirectory(db_session)
        phong = await _phong(db_session, "KD")
        manager = await _nhan_vien(db_session, phong.id, role=Role.MANAGER)
        await _nhan_vien(db_session, phong.id, role=Role.STAFF)

        found = await directory.get_manager_of_department(phong.id)

        assert found is not None
        assert found.user_id == manager.id
        assert found.role == "MANAGER"

    async def test_phong_khong_co_manager_tra_none(self, db_session: AsyncSession) -> None:
        directory = IdentityWorkforceDirectory(db_session)
        phong = await _phong(db_session, "Chua co manager")
        await _nhan_vien(db_session, phong.id, role=Role.STAFF)

        assert await directory.get_manager_of_department(phong.id) is None


async def _hoi_thoai_dong(
    session: AsyncSession,
    department_id,
    assigned_user_id,
    updated_at: datetime,
    status: str = "DA_DONG",
) -> None:
    """Chèn thẳng một hội thoại inbox ở trạng thái cho trước để tính KPI."""
    # Cần channel + customer vì conversations có FK. Tạo tối thiểu.
    ch = await session.execute(
        text(
            "INSERT INTO channels (id, platform, external_channel_id, name, credential, "
            "department_id, is_active, created_at, updated_at) VALUES "
            "(gen_random_uuid(), 'ZALO', :ext, 'OA', 'enc::x', :dept, true, :bg, :bg) RETURNING id"
        ),
        {"ext": f"oa_{new_id().hex}", "dept": str(department_id), "bg": BAY_GIO},
    )
    channel_id = ch.scalar_one()
    cu = await session.execute(
        text(
            "INSERT INTO customers (id, channel_id, platform, external_id, display_name, "
            "avatar_url, created_at, updated_at) VALUES "
            "(gen_random_uuid(), :ch, 'ZALO', :ext, 'K', NULL, :bg, :bg) RETURNING id"
        ),
        {"ch": channel_id, "ext": f"c_{new_id().hex}", "bg": BAY_GIO},
    )
    customer_id = cu.scalar_one()
    await session.execute(
        text(
            "INSERT INTO conversations (id, channel_id, customer_id, status, department_id, "
            "assigned_user_id, last_message_at, created_at, updated_at) VALUES "
            "(gen_random_uuid(), :ch, :cu, :st, :dept, :asg, :bg, :bg, :upd)"
        ),
        {
            "ch": channel_id,
            "cu": customer_id,
            "st": status,
            "dept": str(department_id),
            "asg": str(assigned_user_id) if assigned_user_id else None,
            "bg": BAY_GIO,
            "upd": updated_at,
        },
    )


class TestInboxPerformanceSource:
    async def test_dem_hoi_thoai_dong_cho_nhan_vien(self, db_session: AsyncSession) -> None:
        source = InboxPerformanceSource(db_session)
        phong, nv = new_id(), new_id()
        # 2 hội thoại đóng trong kỳ (tháng 8), gán cho nv.
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2026, 8, 10, tzinfo=UTC))
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2026, 8, 20, tzinfo=UTC))
        # 1 hội thoại đóng ngoài kỳ (tháng 7) — không tính.
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2026, 7, 30, tzinfo=UTC))
        # 1 hội thoại chưa đóng — không tính.
        await _hoi_thoai_dong(
            db_session, phong, nv, datetime(2026, 8, 15, tzinfo=UTC), status="DANG_MO"
        )
        await db_session.flush()

        so = await source.get_metric_for_user(nv, KpiMetricType.CONVERSATIONS_CLOSED, KY)

        assert so == Decimal("2")

    async def test_dem_theo_phong(self, db_session: AsyncSession) -> None:
        source = InboxPerformanceSource(db_session)
        phong_a, phong_b = new_id(), new_id()
        await _hoi_thoai_dong(db_session, phong_a, new_id(), datetime(2026, 8, 10, tzinfo=UTC))
        await _hoi_thoai_dong(db_session, phong_b, new_id(), datetime(2026, 8, 10, tzinfo=UTC))
        await db_session.flush()

        so = await source.get_metric_for_department(phong_a, KpiMetricType.CONVERSATIONS_CLOSED, KY)

        assert so == Decimal("1")

    async def test_bien_ky_la_nua_khoang(self, db_session: AsyncSession) -> None:
        # Đóng đúng 00:00:00 ngày 1 tháng sau KHÔNG thuộc kỳ tháng 8 (biên phải mở).
        source = InboxPerformanceSource(db_session)
        phong, nv = new_id(), new_id()
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2026, 9, 1, 0, 0, tzinfo=UTC))
        # Cuối kỳ hợp lệ: 31/08 23:59 vẫn được đếm.
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2026, 8, 31, 23, 59, tzinfo=UTC))
        await db_session.flush()

        so = await source.get_metric_for_user(nv, KpiMetricType.CONVERSATIONS_CLOSED, KY)

        assert so == Decimal("1")

    async def test_ky_thang_12_khong_tran_nam(self, db_session: AsyncSession) -> None:
        # Kỳ tháng 12/2026: biên phải là 01/01/2027, không lỗi tràn tháng.
        source = InboxPerformanceSource(db_session)
        phong, nv = new_id(), new_id()
        ky_12 = KpiPeriod(year=2026, month=12)
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2026, 12, 15, tzinfo=UTC))
        await _hoi_thoai_dong(db_session, phong, nv, datetime(2027, 1, 1, 0, 0, tzinfo=UTC))
        await db_session.flush()

        so = await source.get_metric_for_user(nv, KpiMetricType.CONVERSATIONS_CLOSED, ky_12)

        assert so == Decimal("1")

    async def test_avg_response_chua_lam_tra_none(self, db_session: AsyncSession) -> None:
        source = InboxPerformanceSource(db_session)

        so = await source.get_metric_for_user(new_id(), KpiMetricType.AVG_RESPONSE_MINUTES, KY)

        assert so is None
