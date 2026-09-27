"""conversation_events: thêm phòng + lý do cho dòng phân phòng (redesign 2b)

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-09-27
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CU = "kind IN ('TAKEN','AUTO_ASSIGNED','ASSIGNED','REASSIGNED','UNASSIGNED')"
_MOI = (
    "kind IN ('TAKEN','AUTO_ASSIGNED','ASSIGNED','REASSIGNED','UNASSIGNED',"
    "'DEPARTMENT_ASSIGNED','AUTO_ROUTED')"
)


def upgrade() -> None:
    op.add_column(
        "conversation_events",
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("conversation_events", sa.Column("detail", sa.Text(), nullable=True))
    op.drop_constraint("ck_conversation_event_kind", "conversation_events", type_="check")
    op.create_check_constraint("ck_conversation_event_kind", "conversation_events", _MOI)


def downgrade() -> None:
    # Bỏ dòng loại mới trước, không thì ràng buộc cũ không dựng lại được.
    op.execute(
        "DELETE FROM conversation_events WHERE kind IN ('DEPARTMENT_ASSIGNED','AUTO_ROUTED')"
    )
    op.drop_constraint("ck_conversation_event_kind", "conversation_events", type_="check")
    op.create_check_constraint("ck_conversation_event_kind", "conversation_events", _CU)
    op.drop_column("conversation_events", "detail")
    op.drop_column("conversation_events", "department_id")
