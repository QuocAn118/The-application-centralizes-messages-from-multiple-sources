"""ORM model cho bảng người dùng."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class UserModel(Base):
    """Bảng ``users`` — chứa cả ba vai trò Staff, Manager và Admin."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # Email duy nhất vĩnh viễn, kể cả với tài khoản đã vô hiệu hoá.
        Index("uq_user_email", func.lower(email), unique=True),
        # Mỗi phòng ban tối đa một quản lý đang hoạt động. Ràng buộc này phải
        # nằm ở cơ sở dữ liệu: kiểm tra ở tầng ứng dụng không chặn được hai
        # request xảy ra đồng thời.
        Index(
            "uq_department_active_manager",
            "department_id",
            unique=True,
            postgresql_where=text("role = 'MANAGER' AND is_active"),
        ),
        CheckConstraint(
            "role IN ('STAFF', 'MANAGER', 'ADMIN')", name="ck_user_role_hop_le"
        ),
        # Staff và Manager bắt buộc thuộc phòng ban; Admin bắt buộc không.
        CheckConstraint(
            "(role = 'ADMIN' AND department_id IS NULL) "
            "OR (role IN ('STAFF', 'MANAGER') AND department_id IS NOT NULL)",
            name="ck_user_phong_ban_khop_vai_tro",
        ),
        Index("ix_user_department_id", "department_id"),
        Index("ix_user_is_active", "is_active"),
    )
