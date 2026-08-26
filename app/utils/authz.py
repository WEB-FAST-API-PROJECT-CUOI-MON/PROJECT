"""Helper dùng chung để kiểm tra quyền truy cập công trình (site) và ghi activity log.

Được dùng bởi router site/team/work_item để tránh lặp lại logic kiểm tra thành viên/owner.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.site import Site, SiteMember, SiteMemberRole
from app.models.user import User


def get_site_or_404(db: Session, site_id: int) -> Site:
    site = db.query(Site).filter(Site.id == site_id, Site.is_deleted.is_(False)).first()
    if not site:
        raise HTTPException(status_code=404, detail="Không tìm thấy công trình")
    return site


def get_membership(db: Session, site_id: int, user_id: int) -> SiteMember | None:
    return (
        db.query(SiteMember)
        .filter(SiteMember.site_id == site_id, SiteMember.user_id == user_id)
        .first()
    )


def require_member(db: Session, site_id: int, current_user: User) -> SiteMember:
    membership = get_membership(db, site_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không phải thành viên của công trình này",
        )
    return membership


def require_owner(db: Session, site_id: int, current_user: User) -> SiteMember:
    membership = require_member(db, site_id, current_user)
    if membership.role != SiteMemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ chủ sở hữu công trình mới được thực hiện hành động này",
        )
    return membership


def log_activity(
    db: Session, user_id: int, site_id: int | None, action: str, detail: str | None = None
) -> None:
    db.add(ActivityLog(user_id=user_id, site_id=site_id, action=action, detail=detail))
