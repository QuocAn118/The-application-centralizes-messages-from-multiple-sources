"""them schema Procrastinate (hang doi job nen) vao cung mot nguon su that Alembic

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-15 09:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Bảng/kiểu/hàm/trigger của Procrastinate đều mang tiền tố ``procrastinate_``,
# không đụng tên nào của ứng dụng — nên gỡ sạch được bằng cách xoá theo tiền tố.
_BANG = (
    "procrastinate_events",
    "procrastinate_periodic_defers",
    "procrastinate_jobs",
    "procrastinate_workers",
)
_KIEU = (
    "procrastinate_job_event_type",
    "procrastinate_job_status",
    "procrastinate_job_to_defer_v1",
)


def upgrade() -> None:
    """Tạo schema hàng đợi bằng chính SQL mà Procrastinate phát hành.

    **Vì sao bọc vào Alembic thay vì chạy ``procrastinate schema --apply``:** dự
    án đã có nguyên tắc "một nguồn sự thật cho schema" — mọi thay đổi cấu trúc DB
    đều đi qua Alembic. Để Procrastinate tự quản lý bảng của nó sẽ tạo ra hệ
    thống migration thứ hai: người dựng môi trường mới phải nhớ chạy đúng hai
    lệnh theo đúng thứ tự, và ``alembic upgrade head`` không còn đủ để có một DB
    chạy được. Bọc vào đây giữ cho một lệnh duy nhất vẫn dựng được toàn bộ.

    SQL được đọc từ ``SchemaManager.get_schema()`` *tại thời điểm chạy migration*
    thay vì chép cứng vào file: bản chép cứng sẽ âm thầm lệch khi nâng cấp
    Procrastinate. Đổi lại, migration này phụ thuộc phiên bản thư viện đang cài —
    ghi rõ trong ADR, và nâng cấp Procrastinate cần một revision mới.
    """
    from procrastinate.schema import SchemaManager

    op.execute(SchemaManager.get_schema())


def downgrade() -> None:
    """Gỡ toàn bộ schema hàng đợi.

    Xoá bảng trước (CASCADE cuốn theo trigger/index/khoá ngoại), rồi tới kiểu và
    hàm. Job đang chờ trong hàng đợi sẽ MẤT — chấp nhận được vì hạ revision là
    thao tác chủ động của người vận hành, và phân tích lỡ mất có thể kích hoạt
    lại thủ công từ giao diện Manager.
    """
    for bang in _BANG:
        op.execute(f"DROP TABLE IF EXISTS {bang} CASCADE")
    for kieu in _KIEU:
        op.execute(f"DROP TYPE IF EXISTS {kieu} CASCADE")

    # Hàm của Procrastinate đều có tiền tố chung; xoá theo danh sách tra từ
    # catalog để không phải liệt kê cứng (số lượng đổi theo phiên bản).
    op.execute(
        """
        DO $$
        DECLARE r RECORD;
        BEGIN
            FOR r IN
                SELECT p.oid::regprocedure AS sig
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public' AND p.proname LIKE 'procrastinate\\_%'
            LOOP
                EXECUTE 'DROP FUNCTION IF EXISTS ' || r.sig || ' CASCADE';
            END LOOP;
        END $$;
        """
    )
