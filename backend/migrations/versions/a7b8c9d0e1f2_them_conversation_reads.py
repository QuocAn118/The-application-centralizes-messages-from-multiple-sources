"""them bang conversation_reads (chua doc theo tung nguoi) + index tin vao

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-27 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """BE-1 (redesign 2a): trạng thái đã đọc THEO TỪNG NGƯỜI + index phục vụ đếm.

    ``conversation_reads``: một dòng cho mỗi (người, hội thoại) đã từng mở. Không
    có dòng = chưa đọc tin nào. Không khoá ngoại sang ``users`` (inbox tham chiếu
    identity qua UUID, như mọi bảng chéo module).

    Partial index ``ix_message_inbound_conv_created``: đếm chưa đọc và tính "khách
    đã chờ" (BE-9) đều chỉ quét tin VÀO của một nhóm hội thoại theo thời gian.
    Chỉ thêm, không đổi bảng cũ — tương thích ngược.
    """
    op.create_table(
        "conversation_reads",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "conversation_id"),
    )
    # CONCURRENTLY: không khoá ghi bảng ``messages`` trong lúc dựng (webhook vẫn nhận
    # tin). PostgreSQL cấm lệnh này trong transaction → ``autocommit_block`` commit
    # phần trước (bảng ``conversation_reads``) rồi chạy lệnh ngoài transaction.
    # Hỏng giữa chừng để lại index INVALID: ``DROP INDEX CONCURRENTLY`` rồi chạy lại.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_message_inbound_conv_created",
            "messages",
            ["conversation_id", "created_at"],
            unique=False,
            postgresql_where=sa.text("direction = 'INBOUND'"),
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    """Gỡ index và bảng — không đụng dữ liệu tin nhắn."""
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_message_inbound_conv_created",
            table_name="messages",
            postgresql_concurrently=True,
        )
    op.drop_table("conversation_reads")
