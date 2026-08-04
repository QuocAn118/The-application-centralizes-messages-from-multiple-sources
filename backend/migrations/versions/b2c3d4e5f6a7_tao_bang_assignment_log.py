"""tao bang assignment_log

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-04 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Tạo bảng ``assignment_log`` — lịch sử mỗi lần gán thành công (#3).

    Không khoá ngoại (chỉ UUID thuần — #3 độc lập). Index theo ``assigned_at`` để
    #5 backfill quét theo khoảng ngày; index theo ``user_id`` để gom theo nhân viên.
    """
    op.create_table(
        "assignment_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assignment_log_assigned_at", "assignment_log", ["assigned_at"])
    op.create_index("ix_assignment_log_user_id", "assignment_log", ["user_id"])


def downgrade() -> None:
    """Xoá bảng ``assignment_log``."""
    op.drop_index("ix_assignment_log_user_id", table_name="assignment_log")
    op.drop_index("ix_assignment_log_assigned_at", table_name="assignment_log")
    op.drop_table("assignment_log")
