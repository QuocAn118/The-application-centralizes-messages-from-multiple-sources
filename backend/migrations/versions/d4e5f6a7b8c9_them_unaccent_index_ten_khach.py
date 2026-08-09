"""them extension unaccent va index tim kiem ten khach

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-09 12:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Bật ``unaccent`` và đánh index cho tìm kiếm tên khách không dấu.

    Người dùng Việt thường gõ không dấu ("nguyen" thay vì "Nguyễn"), nên tìm
    kiếm phải bỏ dấu cả hai vế. ``unaccent`` là extension chuẩn đi kèm bản phân
    phối PostgreSQL (contrib), không phải phụ thuộc ngoài.

    Index dùng ``pg_trgm`` vì mẫu tìm là ``%...%`` — index B-tree thông thường
    không giúp gì cho tiền tố mở. Cả hai hàm trong biểu thức index phải là
    IMMUTABLE, nên ``unaccent`` được gọi qua schema đầy đủ ``public.unaccent``
    với một wrapper immutable: ``unaccent(text)`` mặc định chỉ STABLE.
    """
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Wrapper IMMUTABLE để dùng được trong biểu thức index. An toàn vì từ điển
    # unaccent mặc định không đổi trong vòng đời một cài đặt.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.immutable_unaccent(text)
        RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS
        $$ SELECT public.unaccent('public.unaccent', $1) $$
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_customers_display_name_unaccent
        ON customers
        USING gin (lower(public.immutable_unaccent(display_name)) gin_trgm_ops)
        """
    )


def downgrade() -> None:
    """Bỏ index và hàm wrapper.

    Cố ý KHÔNG ``DROP EXTENSION``: extension có thể đang được thứ khác dùng, và
    bỏ nó đi rủi ro hơn nhiều so với việc để lại.
    """
    op.execute("DROP INDEX IF EXISTS ix_customers_display_name_unaccent")
    op.execute("DROP FUNCTION IF EXISTS public.immutable_unaccent(text)")
