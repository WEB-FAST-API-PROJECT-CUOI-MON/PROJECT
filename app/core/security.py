"""Xử lý băm mật khẩu và tạo/giải mã JWT token (access + refresh)."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Băm mật khẩu bằng bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """So khớp mật khẩu người dùng nhập với mật khẩu đã băm trong DB."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def _create_token(data: dict, token_type: str, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Tạo JWT access token (thời hạn ngắn) chứa payload `data`."""
    return _create_token(
        data,
        token_type="access",
        expires_delta=expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Tạo JWT refresh token (thời hạn dài hơn) dùng để cấp lại access token."""
    return _create_token(
        data,
        token_type="refresh",
        expires_delta=expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    """Giải mã JWT token.

    Không nuốt lỗi ở đây: để nguyên jwt.ExpiredSignatureError / jwt.PyJWTError
    cho caller tự phân biệt "hết hạn" và "không hợp lệ" để trả message phù hợp.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
