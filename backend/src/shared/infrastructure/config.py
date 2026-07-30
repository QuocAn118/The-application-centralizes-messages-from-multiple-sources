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

    # Inbox: bí mật cấp ứng dụng để verify chữ ký webhook (không phải token kênh).
    zalo_app_id: str = ""
    zalo_oa_secret_key: str = ""
    meta_app_secret: str = ""
    # Token dùng khi Meta/Zalo verify webhook (GET hub.challenge). Rỗng = bỏ qua.
    webhook_verify_token: str = ""

    # Keyword (#2): Claude API để LLM tự đọc tin và chọn phòng phù hợp.
    # Khoá là BÍ MẬT — chỉ đọc từ .env, không commit, không log.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    # Múi giờ nghiệp vụ: giờ ca làm (#4) và các so sánh "đang trong ca" (#3) diễn
    # ra theo giờ địa phương này, dù hệ thống lưu mọi mốc thời gian ở UTC. Nhân
    # viên nhập "ca sáng 08:00" theo giờ VN, không phải UTC.
    app_timezone: str = "Asia/Ho_Chi_Minh"

    app_env: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Trả về cấu hình đã cache, tránh đọc lại file ``.env`` mỗi lần gọi."""
    return Settings()  # type: ignore[call-arg]
