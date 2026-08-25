"""API cho User."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.user import UserOut

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    """Lấy thông tin user đang đăng nhập."""
    return current_user


@router.get("", response_model=list[UserOut])
def list_users(
    search: str | None = Query(None, description="Tìm theo họ tên hoặc email"),
    is_active: bool | None = Query(None, description="Lọc theo trạng thái tài khoản"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Lấy danh sách người dùng — chỉ Admin, hỗ trợ search theo tên/email và lọc trạng thái."""
    query = db.query(User)
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    return query.all()
