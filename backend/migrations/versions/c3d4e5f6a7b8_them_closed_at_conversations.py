"""them cot closed_at vao conversations

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-05 09:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Thêm cột ``closed_at`` (nullable) và backfill mốc đóng cho dữ liệu cũ.

    Cột nullable nên đây là mở rộng tương thích ngược (không phá schema #1 hiện có).
    Dữ liệu cũ đã ``DA_DONG`` chưa có mốc đóng chính xác → backfill bằng
    ``updated_at`` (đúng proxy #4/#5 vẫn dùng cho các dòng cũ). Từ nay ``close()``
    ghi ``closed_at`` chính xác, mở lại xoá về NULL.
    """
    op.add_column(
        "conversations",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE conversations SET closed_at = updated_at WHERE status = 'DA_DONG'"
    )


def downgrade() -> None:
    """Xoá cột ``closed_at``."""
    op.drop_column("conversations", "closed_at")
