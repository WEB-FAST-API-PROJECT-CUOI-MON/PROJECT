"""Dependency xác thực người dùng và kiểm tra quyền (role)."""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.database import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Giải mã access token, trả về user hiện tại hoặc raise lỗi với status/message phù hợp."""
    try:
        payload = decode_token(token)
    
    # Bắt lỗi khi token quá hạn sử dụng
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token đã hết hạn, vui lòng đăng nhập lại",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Bắt tất cả các lỗi JWT còn lại (sai chữ ký, sai định dạng, token bị can thiệp...)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Chỉ chấp nhận access token ở đây, không cho dùng refresh token thay thế.
    if payload.get("type") != "access" or payload.get("sub") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.email == payload["sub"]).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa, vui lòng liên hệ quản trị viên",
        )

    return user


def require_role(*allowed_roles: UserRole):
    """Dependency factory: chỉ cho phép các role được liệt kê truy cập endpoint."""

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện hành động này",
            )
        return current_user

    return checker
