"""ORM model cho bảng kênh kết nối."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class ChannelModel(Base):
    """Bảng ``channels``.

    ``department_id`` là UUID thuần tham chiếu identity — cố ý **không** khoá
    ngoại sang bảng ``departments`` để giữ module inbox độc lập (spec §8).
    ``credential`` lưu bản đã mã hoá; không bao giờ lưu token thô.
    """

    __tablename__ = "channels"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    external_channel_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    credential: Mapped[str] = mapped_column(Text, nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # Mỗi (nền tảng + mã kênh) chỉ kết nối một lần — webhook tra kênh theo đây.
        Index(
            "uq_channel_platform_external",
            "platform",
            "external_channel_id",
            unique=True,
        ),
        CheckConstraint(
            "platform IN ('ZALO', 'FACEBOOK', 'INSTAGRAM')",
            name="ck_channel_platform_hop_le",
        ),
        Index("ix_channel_department_id", "department_id"),
        Index("ix_channel_is_active", "is_active"),
    )
