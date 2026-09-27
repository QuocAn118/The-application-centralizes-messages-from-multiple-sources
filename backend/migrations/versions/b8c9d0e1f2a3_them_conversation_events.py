"""them bang conversation_events (timeline nhan/giao/doi/go nguoi phu trach)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-27 14:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """BE-2 (redesign 2a): timeline sự kiện người phụ trách — nguồn dòng hệ thống.

    Bảng riêng của Hộp thư, KHÔNG sửa ``assignment_log`` (#3/#5 giữ nguyên nghĩa).
    Chỉ thêm — tương thích ngược. Hội thoại cũ không có sự kiện (timeline bắt đầu
    từ lúc triển khai).
    """
    op.create_table(
        "conversation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('TAKEN','AUTO_ASSIGNED','ASSIGNED','REASSIGNED','UNASSIGNED')",
            name="ck_conversation_event_kind",
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_event_conv_created",
        "conversation_events",
        ["conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_event_conv_created", table_name="conversation_events")
    op.drop_table("conversation_events")
