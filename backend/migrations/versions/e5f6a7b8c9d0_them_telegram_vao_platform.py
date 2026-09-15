"""them TELEGRAM vao CHECK constraint cot platform cua bang channels

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-14 09:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TEN_RANG_BUOC = "ck_channel_platform_hop_le"
_CU = "platform IN ('ZALO', 'FACEBOOK', 'INSTAGRAM')"
_MOI = "platform IN ('ZALO', 'FACEBOOK', 'INSTAGRAM', 'TELEGRAM')"


def upgrade() -> None:
    """Cho phép kênh Telegram.

    PostgreSQL không sửa được biểu thức của một CHECK constraint tại chỗ, nên
    phải xoá rồi tạo lại. Migration cũ **không** bị sửa: lịch sử migration là
    bất biến, sửa file cũ sẽ làm hai máy cùng revision mà khác schema.

    Vì sao vẫn giữ CHECK thay vì bỏ hẳn: cột ``platform`` là VARCHAR (quyết định
    ở #0 — ENUM của PostgreSQL cần ``ALTER TYPE`` phiền khi migrate), nên CHECK
    là thứ duy nhất chặn giá trị rác lọt vào từ một lỗi ghi bất kỳ.
    """
    op.drop_constraint(_TEN_RANG_BUOC, "channels", type_="check")
    op.create_check_constraint(_TEN_RANG_BUOC, "channels", _MOI)


def downgrade() -> None:
    """Thu hẹp lại ba nền tảng cũ.

    Chặn trước nếu còn kênh TELEGRAM: tạo lại constraint cũ khi dữ liệu vi phạm
    sẽ làm PostgreSQL ném lỗi giữa chừng, để lại bảng không có constraint nào.
    Báo lỗi rõ ràng tốt hơn là hỏng nửa vời.
    """
    conn = op.get_bind()
    con_lai = conn.exec_driver_sql(
        "SELECT count(*) FROM channels WHERE platform = 'TELEGRAM'"
    ).scalar()
    if con_lai:
        raise RuntimeError(
            f"Còn {con_lai} kênh TELEGRAM trong bảng channels. "
            "Xoá hoặc đổi nền tảng cho các kênh đó trước khi hạ revision này."
        )
    op.drop_constraint(_TEN_RANG_BUOC, "channels", type_="check")
    op.create_check_constraint(_TEN_RANG_BUOC, "channels", _CU)
