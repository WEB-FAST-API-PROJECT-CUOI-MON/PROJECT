"""Đọc cấu hình ứng dụng từ biến môi trường / file .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Không đặt giá trị mặc định cho các field nhạy cảm (DATABASE_URL, SECRET_KEY):
    bắt buộc phải khai báo trong .env, thiếu thì app raise lỗi ngay khi khởi động
    thay vì âm thầm chạy với secret yếu/lộ trong code.
    """

    PROJECT_NAME: str = "Construction Management API"

    # Database — bắt buộc khai báo trong .env, không có default.
    DATABASE_URL: str

    # JWT — bắt buộc khai báo trong .env, không có default.
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 ngày
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Rate limit chống brute-force cho /auth/login (mức demo, in-memory)
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
