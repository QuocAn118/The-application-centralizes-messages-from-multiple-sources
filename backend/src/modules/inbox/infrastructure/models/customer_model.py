"""ORM model cho bảng khách hàng."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class CustomerModel(Base):
    """Bảng ``customers``.

    Unique (channel_id, external_id): mỗi kênh giữ hồ sơ khách riêng, không gộp
    danh tính đa kênh (spec §3, §10). ``channel_id`` là khoá ngoại **trong nội
    bộ module inbox** nên được phép — ràng buộc cấm chỉ áp cho khoá ngoại *sang
    identity*.
    """

    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    channel_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "uq_customer_channel_external",
            "channel_id",
            "external_id",
            unique=True,
        ),
    )
