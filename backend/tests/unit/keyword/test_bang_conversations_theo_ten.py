"""Chốt phụ thuộc DỮ LIỆU của keyword vào bảng ``conversations`` của inbox.

``analysis_repository`` tham chiếu bảng theo TÊN (``sqlalchemy.table``) để không
import inbox (import-linter cấm). Cái giá: đổi tên bảng/cột thì mypy lẫn
import-linter đều im lặng. Test này là chỗ báo — xem
docs/superpowers/adr/2026-09-28-doc-bang-conversations-xuyen-module.md.

Test được phép import inbox: import-linter chỉ soát ``src``.
"""

from src.modules.inbox.infrastructure.models.conversation_model import ConversationModel
from src.modules.keyword.infrastructure.repositories.analysis_repository import _HOI_THOAI


def test_ten_bang_va_cot_khop_model_inbox() -> None:
    bang = ConversationModel.__table__
    assert _HOI_THOAI.name == bang.name
    for cot in _HOI_THOAI.c:
        assert cot.name in bang.c, f"cột {cot.name!r} không còn trong {bang.name}"


def test_department_id_van_nhan_null() -> None:
    # "Chờ phân phòng" = department_id IS NULL. Cột thôi nhận NULL thì Manager
    # mất hàng chờ phân mà không có lỗi nào.
    assert ConversationModel.__table__.c.department_id.nullable is True
