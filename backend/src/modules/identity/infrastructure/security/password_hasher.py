"""Băm mật khẩu bằng bcrypt."""

import base64
import hashlib

import bcrypt


class BcryptPasswordHasher:
    """Băm mật khẩu bằng bcrypt.

    Bcrypt tự sinh salt cho mỗi lần băm, nên hai người dùng đặt cùng mật khẩu
    vẫn có hash khác nhau.

    Mật khẩu được rút gọn bằng SHA-256 trước khi đưa vào bcrypt — xem
    ``_rut_gon`` để biết lý do.
    """

    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    @staticmethod
    def _rut_gon(plain_password: str) -> bytes:
        """Rút gọn mật khẩu về 44 byte cố định bằng SHA-256 rồi base64.

        Bcrypt chỉ nhận tối đa 72 byte và từ phiên bản 4.1 trở đi nó **ném
        ``ValueError``** thay vì lặng lẽ cắt bớt. Cắt thủ công ở byte 72 cũng
        không ổn: mật khẩu tiếng Việt có dấu dùng nhiều byte cho mỗi ký tự
        (140 ký tự có thể thành 195 byte), nên cắt thô dễ rơi vào giữa một ký
        tự UTF-8 và tạo ra chuỗi byte hỏng.

        Băm SHA-256 trước cho ra độ dài cố định, giữ được toàn bộ entropy của
        mật khẩu gốc dù dài bao nhiêu. Base64 để tránh ký tự NUL — bcrypt cắt
        chuỗi tại byte NUL đầu tiên.
        """
        tom_tat = hashlib.sha256(plain_password.encode("utf-8")).digest()
        return base64.b64encode(tom_tat)

    def hash(self, plain_password: str) -> str:
        muoi = bcrypt.gensalt(rounds=self._rounds)
        return bcrypt.hashpw(self._rut_gon(plain_password), muoi).decode("utf-8")

    def verify(self, plain_password: str, hashed: str) -> bool:
        """So khớp mật khẩu với chuỗi hash.

        Chuỗi hash hỏng trả về ``False`` thay vì ném ngoại lệ, để dữ liệu lỗi
        trong cơ sở dữ liệu không làm sập luồng đăng nhập.
        """
        try:
            return bcrypt.checkpw(self._rut_gon(plain_password), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False
