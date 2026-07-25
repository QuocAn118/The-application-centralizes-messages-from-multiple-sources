"""Lưu tệp đính kèm xuống đĩa local (implementation dev của ``IAttachmentStore``).

URL media của nền tảng hết hạn (RB-4), nên nội dung được tải về và lưu lại. Bản
dev ghi xuống ``ATTACHMENT_STORAGE_DIR``; đổi sang object storage (S3...) sau chỉ
cần thay class này, không đụng use case.
"""

import asyncio
import re
from pathlib import Path
from uuid import uuid4

from src.modules.inbox.domain.ports import StoredAttachment

_TEN_AN_TOAN = re.compile(r"[^A-Za-z0-9._-]+")


def _lam_sach_ten(suggested_name: str) -> str:
    """Chỉ giữ ký tự an toàn; chống path traversal (``..``, dấu ``/``)."""
    ten = _TEN_AN_TOAN.sub("_", suggested_name.strip()).strip("._")
    return ten or "attachment"


class LocalAttachmentStore:
    """Ghi và phục vụ lại tệp đính kèm từ một thư mục trên đĩa."""

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)

    async def save(
        self, data: bytes, suggested_name: str, content_type: str | None
    ) -> StoredAttachment:
        """Lưu ``data`` với tên duy nhất; ``stored_path`` là tên tương đối base_dir.

        Ghi đĩa là I/O chặn, nên đẩy sang thread để không nghẽn event loop. Tên
        gắn tiền tố UUID để không đè nhau dù hai tệp cùng tên gợi ý.
        """
        ten = f"{uuid4().hex}_{_lam_sach_ten(suggested_name)}"
        await asyncio.to_thread(self._ghi, self._base / ten, data)
        return StoredAttachment(
            stored_path=ten,
            content_type=content_type,
            size=len(data),
        )

    def resolve(self, stored_path: str) -> Path:
        """Trả đường dẫn tuyệt đối để phục vụ lại tệp; chống thoát khỏi base_dir."""
        duong_dan = (self._base / stored_path).resolve()
        base = self._base.resolve()
        if base not in duong_dan.parents and duong_dan != base:
            raise ValueError("stored_path không hợp lệ.")
        return duong_dan

    def _ghi(self, duong_dan: Path, data: bytes) -> None:
        duong_dan.parent.mkdir(parents=True, exist_ok=True)
        duong_dan.write_bytes(data)
