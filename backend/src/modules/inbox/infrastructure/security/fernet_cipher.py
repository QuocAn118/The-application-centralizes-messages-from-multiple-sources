"""Mã hoá credential kênh bằng Fernet (AES-128-CBC + HMAC).

Implementation của port ``ICredentialCipher``. Khoá đối xứng đọc từ ``.env``
(`CHANNEL_CIPHER_KEY`), không commit. Đổi sang secret manager (Vault/AWS SM) sau
chỉ cần thay class này, không đụng use case.
"""

from cryptography.fernet import Fernet


class InvalidCipherKeyError(RuntimeError):
    """Khoá Fernet thiếu hoặc sai định dạng."""

    def __init__(self) -> None:
        super().__init__(
            "CHANNEL_CIPHER_KEY thiếu hoặc không hợp lệ. Sinh khoá bằng "
            "Fernet.generate_key() và đặt vào .env."
        )


class FernetCredentialCipher:
    """Mã hoá/giải mã token của kênh trước khi ghi vào DB."""

    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise InvalidCipherKeyError from exc

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
