"""Business logic cho User."""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user import User


def list_users(db: Session, search: str | None, is_active: bool | None) -> list[User]:
    """Lấy danh sách người dùng, hỗ trợ search theo tên/email và lọc trạng thái."""
    query = db.query(User)
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    return query.all()
