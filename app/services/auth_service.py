"""Business logic cho Đăng ký / Đăng nhập / Refresh token."""

import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.rate_limit import check_login_rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate


def _issue_tokens(user: User) -> Token:
    data = {"sub": user.email}
    return Token(
        access_token=create_access_token(data),
        refresh_token=create_refresh_token(data),
    )


def register_user(db: Session, user_in: UserCreate) -> User:
    """Đăng ký tài khoản mới, báo lỗi nếu email đã tồn tại."""
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email đã tồn tại")

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        password_hash=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, request: Request, form_data: OAuth2PasswordRequestForm) -> Token:
    """Đăng nhập bằng email/password (rate-limited), trả về access token + refresh token JWT.

    Lưu ý: chuẩn OAuth2 password grant cố định tên field là "username",
    nhưng ở đây giá trị truyền vào field đó phải là email đăng nhập.
    """
    check_login_rate_limit(request)

    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai email hoặc mật khẩu",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa, vui lòng liên hệ quản trị viên",
        )

    return _issue_tokens(user)


def refresh_access_token(db: Session, refresh_token: str) -> Token:
    """Cấp lại access token (và refresh token mới) từ một refresh token còn hợp lệ."""
    try:
        payload = decode_token(refresh_token)

    # Nếu refresh token này đã quá hạn sử dụng => Báo lỗi
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token đã hết hạn, vui lòng đăng nhập lại",
        )

    # Nếu token bị sai định dạng, bị sửa đổi hoặc chữ ký không khớp => Báo lỗi
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không hợp lệ",
        )

    if payload.get("type") != "refresh" or payload.get("sub") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không hợp lệ",
        )

    user = db.query(User).filter(User.email == payload["sub"]).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token không hợp lệ")
    # Kiểm tra trạng thái tài khoản
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa, vui lòng liên hệ quản trị viên",
        )

    # Cấp token mới
    return _issue_tokens(user)
