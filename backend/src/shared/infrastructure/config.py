"""Cấu hình ứng dụng đọc từ biến môi trường."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Toàn bộ cấu hình của ứng dụng.

    Giá trị lấy từ biến môi trường, hoặc từ file ``.env`` khi chạy cục bộ.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    test_database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300

    # Inbox: khoá Fernet mã hoá credential kênh + nơi lưu tệp đính kèm.
    channel_cipher_key: str = ""
    attachment_storage_dir: str = "var/attachments"

    app_env: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Trả về cấu hình đã cache, tránh đọc lại file ``.env`` mỗi lần gọi."""
    return Settings()  # type: ignore[call-arg]
