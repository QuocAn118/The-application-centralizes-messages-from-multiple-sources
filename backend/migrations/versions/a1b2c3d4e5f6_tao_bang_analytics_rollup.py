"""tao bang analytics rollup

Revision ID: a1b2c3d4e5f6
Revises: dff8571b18ef
Create Date: 2026-07-30 09:15:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "dff8571b18ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Tạo hai bảng rollup của #5 Analytics.

    Khoá gộp có ``department_id`` NULL-able nên dùng unique index
    ``NULLS NOT DISTINCT`` (PostgreSQL 15+) để ``ON CONFLICT`` cộng-delta gộp đúng
    cả dòng chưa phân phòng. Không khoá ngoại — #5 độc lập, chỉ UUID thuần.
    """
    op.create_table(
        "analytics_daily_conversation",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("channel_platform", sa.String(length=20), nullable=False),
        sa.Column("inbound_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("outbound_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opened_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("closed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_analytics_daily_conversation "
        "ON analytics_daily_conversation "
        "(work_date, department_id, channel_platform) NULLS NOT DISTINCT"
    )

    op.create_table(
        "analytics_daily_agent",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("handled_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assigned_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "sum_first_response_seconds", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("first_response_samples", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sum_resolution_seconds", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("resolution_samples", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_analytics_daily_agent "
        "ON analytics_daily_agent "
        "(work_date, user_id, department_id) NULLS NOT DISTINCT"
    )
    # Index phục vụ đọc theo khoảng ngày + lọc phòng.
    op.create_index(
        "ix_analytics_daily_conversation_work_date",
        "analytics_daily_conversation",
        ["work_date"],
    )
    op.create_index(
        "ix_analytics_daily_agent_work_date",
        "analytics_daily_agent",
        ["work_date"],
    )


def downgrade() -> None:
    """Xoá hai bảng rollup."""
    op.drop_index("ix_analytics_daily_agent_work_date", table_name="analytics_daily_agent")
    op.drop_index(
        "ix_analytics_daily_conversation_work_date",
        table_name="analytics_daily_conversation",
    )
    op.execute("DROP INDEX IF EXISTS uq_analytics_daily_agent")
    op.drop_table("analytics_daily_agent")
    op.execute("DROP INDEX IF EXISTS uq_analytics_daily_conversation")
    op.drop_table("analytics_daily_conversation")
