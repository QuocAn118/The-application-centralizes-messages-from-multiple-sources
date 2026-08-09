"""Ký và xác minh URL tạm cho tệp đính kèm.

Vì sao cần: thẻ ``<img>`` của trình duyệt không gửi được header
``Authorization``, nên không thể bảo vệ ảnh bằng Bearer token như các endpoint
khác. Thay vào đó backend cấp một URL mang chữ ký hết hạn sau ít phút — ai không
có chữ ký hợp lệ thì không tải được, và link rò rỉ cũng chỉ dùng được trong thời
gian ngắn.

Chữ ký là HMAC-SHA256 trên ``(attachment_id, conversation_id, hạn)`` với khoá
bí mật của ứng dụng, nên không thể giả mạo hay sửa hạn mà chữ ký còn đúng.
"""

import hashlib
import hmac
import time
from uuid import UUID


class SignedUrlError(Exception):
    """Chữ ký sai, hết hạn, hoặc tham số không hợp lệ."""


class AttachmentUrlSigner:
    """Ký/xác minh tham số truy cập tệp đính kèm."""

    def __init__(self, secret_key: str, ttl_seconds: int = 300) -> None:
        if not secret_key:
            raise ValueError("Khoá ký URL đính kèm không được rỗng.")
        self._secret = secret_key.encode("utf-8")
        self._ttl = ttl_seconds

    @property
    def ttl_seconds(self) -> int:
        return self._ttl

    def _tinh_chu_ky(self, attachment_id: UUID, conversation_id: UUID, het_han: int) -> str:
        # Ghép bằng dấu ":" trên chuỗi UUID có độ dài cố định nên không có nguy cơ
        # nhập nhằng ranh giới trường.
        thong_diep = f"{attachment_id}:{conversation_id}:{het_han}".encode()
        return hmac.new(self._secret, thong_diep, hashlib.sha256).hexdigest()

    def ky(
        self,
        attachment_id: UUID,
        conversation_id: UUID,
        now: float | None = None,
    ) -> tuple[int, str]:
        """Trả ``(hạn, chữ ký)`` cho một tệp đính kèm."""
        moc = int(now if now is not None else time.time())
        het_han = moc + self._ttl
        return het_han, self._tinh_chu_ky(attachment_id, conversation_id, het_han)

    def xac_minh(
        self,
        attachment_id: UUID,
        conversation_id: UUID,
        het_han: int,
        chu_ky: str,
        now: float | None = None,
    ) -> None:
        """Ném ``SignedUrlError`` nếu chữ ký sai hoặc đã hết hạn."""
        moc = int(now if now is not None else time.time())
        if het_han < moc:
            raise SignedUrlError("Liên kết đã hết hạn.")

        mong_doi = self._tinh_chu_ky(attachment_id, conversation_id, het_han)
        # So sánh hằng thời gian: so sánh chuỗi thường rò rỉ thông tin qua thời
        # gian thực thi và cho phép dò dần từng ký tự chữ ký.
        if not hmac.compare_digest(mong_doi, chu_ky):
            raise SignedUrlError("Chữ ký không hợp lệ.")
