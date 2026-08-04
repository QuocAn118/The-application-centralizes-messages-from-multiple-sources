"""ORM model cho hai bảng rollup ngày của #5 (read model riêng).

Cả hai chỉ chứa UUID thuần tham chiếu inbox/identity — không khoá ngoại (giữ #5
độc lập, spec §3). Khoá chính tự nhiên gồm cả chiều báo cáo để UPSERT cộng-delta
dùng ``ON CONFLICT`` trên đúng khoá đó.

``work_date`` là **ngày nghiệp vụ địa phương** (đã quy đổi ``app_timezone``, quy
tắc event-time — xem ``IConversationStatsSource``), lưu kiểu ``Date`` (không giờ).
"""

from datetime import date
from uuid import UUID

from sqlalchemy import BigInteger, Date, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base

# ``department_id`` NULL là một phần khoá (hội thoại chưa phân phòng). PostgreSQL
# coi NULL khác NULL trong UNIQUE/PK thường, nên KHÔNG đặt các cột NULL vào PK;
# thay vào đó dùng một cột thay thế + unique index ``NULLS NOT DISTINCT`` để
# ``ON CONFLICT`` gộp đúng cả dòng có department_id NULL.


class AnalyticsDailyConversationModel(Base):
    """Bảng ``analytics_daily_conversation`` — khối lượng theo ngày/phòng/kênh (#1).

    Khoá gộp: ``(work_date, department_id, channel_platform)`` qua unique index
    ``NULLS NOT DISTINCT`` (department_id có thể NULL). ``id`` chỉ là khoá thay thế.
    """

    __tablename__ = "analytics_daily_conversation"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    channel_platform: Mapped[str] = mapped_column(String(20), nullable=False)
    inbound_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outbound_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    closed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AnalyticsDailyAgentModel(Base):
    """Bảng ``analytics_daily_agent`` — hiệu suất theo ngày/nhân viên/phòng (#1+#3).

    Khoá gộp: ``(work_date, user_id, department_id)`` qua unique index
    ``NULLS NOT DISTINCT``. Thời gian phản hồi/đóng lưu **tổng giây + số mẫu** (kiểu
    ``BigInteger`` cho tổng để không tràn khi cộng dồn nhiều ngày).
    """

    __tablename__ = "analytics_daily_agent"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    handled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assigned_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sum_first_response_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    first_response_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sum_resolution_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    resolution_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
