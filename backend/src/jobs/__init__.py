"""Hàng đợi job nền (Procrastinate) — tầng composition, ngang hàng ``main.py``.

**Vì sao là ``src.jobs`` chứ không nằm trong một module nghiệp vụ:** task phân
tích cần biết cả ``keyword`` (use case phân tích) lẫn ``inbox`` (tra hội thoại từ
sự kiện webhook). Đặt nó trong bất kỳ module nào cũng phá ranh giới
``inbox ⊥ keyword`` mà import-linter đang giữ. Giống ``main.py``, đây là chỗ
*lắp ráp*, được phép biết nhiều module — nên các contract chỉ ràng buộc
``src.modules.*`` vẫn nguyên vẹn.

Không đặt logic nghiệp vụ ở đây: task chỉ điều phối, mọi quyết định vẫn nằm
trong use case của module tương ứng.
"""
