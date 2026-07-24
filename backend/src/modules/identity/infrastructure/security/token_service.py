"""Cấp phát và kiểm tra JWT."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from src.modules.identity.application.ports import (
    AccessTokenPayload,
    ExpiredTokenError,
    InvalidTokenError,
)
from src.modules.identity.domain.value_objects.role import Role
from src.shared.application.ports import IClock


class JwtTokenService:
    """Cấp access token dạng JWT và refresh token dạng chuỗi ngẫu nhiên.

    Access token là JWT tự chứa thông tin, không cần tra cứu cơ sở dữ liệu khi
    kiểm tra. Refresh token ngược lại chỉ là chuỗi ngẫu nhiên, phải đối chiếu
    với bản ghi trong cơ sở dữ liệu — nhờ đó thu hồi được.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        access_token_expire_minutes: int,
        clock: IClock,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self._clock = clock

    def create_access_token(
        self, user_id: UUID, role: Role, department_id: UUID | None
    ) -> str:
        bay_gio = self._clock.now()
        het_han = bay_gio + self._access_token_expire
        noi_dung = {
            "sub": str(user_id),
            "role": role.value,
            "dept": str(department_id) if department_id else None,
            "iat": int(bay_gio.timestamp()),
            "exp": int(het_han.timestamp()),
        }
        return jwt.encode(noi_dung, self._secret_key, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> AccessTokenPayload:
        """Giải mã token và tự kiểm tra hạn theo ``IClock``.

        ``verify_exp`` được tắt có chủ đích: PyJWT so ``exp`` với đồng hồ hệ
        thống thật, bỏ qua ``IClock``. Nếu để PyJWT tự kiểm tra thì test không
        điều khiển được thời gian, và mọi test dùng mốc thời gian cố định sẽ
        cho kết quả phụ thuộc vào lúc chạy. Chữ ký vẫn được PyJWT xác minh —
        phần bị tắt chỉ là so sánh thời gian, và nó được làm lại ngay bên dưới.
        """
        try:
            noi_dung = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"require": ["sub", "exp", "iat"], "verify_exp": False},
            )
        except jwt.PyJWTError as loi:
            raise InvalidTokenError from loi

        try:
            ma_phong = noi_dung["dept"]
            phat_hanh = datetime.fromtimestamp(noi_dung["iat"], tz=UTC)
            het_han = datetime.fromtimestamp(noi_dung["exp"], tz=UTC)
            payload = AccessTokenPayload(
                user_id=UUID(noi_dung["sub"]),
                role=Role(noi_dung["role"]),
                department_id=UUID(ma_phong) if ma_phong else None,
                issued_at=phat_hanh,
                expires_at=het_han,
            )
        except (KeyError, ValueError) as loi:
            raise InvalidTokenError from loi

        if self._clock.now() >= het_han:
            raise ExpiredTokenError
        return payload

    def create_refresh_token(self) -> tuple[str, str]:
        """Sinh refresh token 43 ký tự từ nguồn ngẫu nhiên an toàn mật mã."""
        tho = secrets.token_urlsafe(32)
        return tho, self.hash_refresh_token(tho)

    def hash_refresh_token(self, token: str) -> str:
        """Băm bằng SHA-256.

        Không dùng bcrypt ở đây: refresh token đã là chuỗi ngẫu nhiên 256 bit
        nên không sợ tấn công từ điển, và SHA-256 cho phép tra cứu trực tiếp
        theo hash trong cơ sở dữ liệu.
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
