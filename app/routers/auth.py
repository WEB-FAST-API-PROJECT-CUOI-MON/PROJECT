"""Đăng ký, Đăng nhập, Refresh token."""

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.token import RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản mới",
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Đăng ký tài khoản mới."""
    return auth_service.register_user(db, user_in)


@router.post("/login", response_model=Token, summary="Đăng nhập")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Đăng nhập bằng email/password, trả về access token + refresh token JWT.

    Lưu ý: chuẩn OAuth2 password grant cố định tên field là "username",
    nhưng ở đây giá trị truyền vào field đó phải là email đăng nhập.
    """
    return auth_service.login_user(db, request, form_data)


@router.post("/refresh", response_model=Token, summary="Làm mới access token")
def refresh_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Cấp lại access token (và refresh token mới) từ một refresh token còn hợp lệ."""
    return auth_service.refresh_access_token(db, body.refresh_token)
