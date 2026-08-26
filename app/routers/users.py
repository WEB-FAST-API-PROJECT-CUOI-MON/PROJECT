"""API cho User."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.user import UserOut
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut, summary="Thông tin user hiện tại")
def read_current_user(current_user: User = Depends(get_current_user)):
    """Lấy thông tin user đang đăng nhập."""
    return current_user


@router.get("", response_model=list[UserOut], summary="Danh sách người dùng (chỉ Admin)")
def list_users(
    search: str | None = Query(None, description="Tìm theo họ tên hoặc email"),
    is_active: bool | None = Query(None, description="Lọc theo trạng thái tài khoản"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Lấy danh sách người dùng — chỉ Admin, hỗ trợ search theo tên/email và lọc trạng thái."""
    return user_service.list_users(db, search, is_active)
