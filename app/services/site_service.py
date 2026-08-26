"""Business logic cho Công trình và Thành viên công trình."""

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.site import Site, SiteMember, SiteMemberRole
from app.models.user import User
from app.schemas.site import SiteCreate, SiteMemberAdd, SiteUpdate
from app.utils.authz import get_membership, get_site_or_404, log_activity, require_member, require_owner

# --- Công trình ---


def create_site(db: Session, site_in: SiteCreate, current_user: User) -> Site:
    """Tạo công trình mới, người tạo tự động trở thành OWNER."""
    site = Site(**site_in.model_dump(), owner_id=current_user.id)
    db.add(site)
    db.flush()  # cần site.id trước khi tạo SiteMember

    db.add(SiteMember(site_id=site.id, user_id=current_user.id, role=SiteMemberRole.OWNER))
    log_activity(db, current_user.id, site.id, "SITE_CREATED", f"Tạo công trình '{site.name}'")

    db.commit()
    db.refresh(site)
    return site


def list_sites(db: Session, current_user: User, search: str | None) -> list[Site]:
    """Lấy danh sách công trình mà user hiện tại là owner/member; hỗ trợ tìm theo tên."""
    query = (
        db.query(Site)
        .join(SiteMember, SiteMember.site_id == Site.id)
        .filter(SiteMember.user_id == current_user.id, Site.is_deleted.is_(False))
    )
    if search:
        query = query.filter(Site.name.ilike(f"%{search}%"))
    return query.order_by(Site.created_at.desc()).all()


def get_site_detail(db: Session, site_id: int, current_user: User) -> Site:
    """Lấy chi tiết một công trình, chỉ thành viên công trình mới được xem."""
    site = get_site_or_404(db, site_id)
    require_member(db, site_id, current_user)
    return site


def update_site(db: Session, site_id: int, site_in: SiteUpdate, current_user: User) -> Site:
    """Cập nhật công trình, chỉ OWNER được sửa."""
    site = get_site_or_404(db, site_id)
    require_owner(db, site_id, current_user)

    data = site_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(site, field, value)

    log_activity(db, current_user.id, site.id, "SITE_UPDATED", f"Cập nhật công trình: {sorted(data.keys())}")

    db.commit()
    db.refresh(site)
    return site


def delete_site(db: Session, site_id: int, current_user: User) -> None:
    """Xóa công trình (soft delete), chỉ OWNER được xóa."""
    site = get_site_or_404(db, site_id)
    require_owner(db, site_id, current_user)

    site.is_deleted = True
    site.deleted_at = func.now()
    log_activity(db, current_user.id, site.id, "SITE_DELETED", f"Xóa công trình '{site.name}'")

    db.commit()


# --- Thành viên công trình ---


def list_site_members(db: Session, site_id: int, current_user: User) -> list[SiteMember]:
    """Danh sách thành viên và role trong công trình."""
    get_site_or_404(db, site_id)
    require_member(db, site_id, current_user)
    return (
        db.query(SiteMember)
        .filter(SiteMember.site_id == site_id)
        .order_by(SiteMember.joined_at.asc())
        .all()
    )


def add_site_member(db: Session, site_id: int, member_in: SiteMemberAdd, current_user: User) -> SiteMember:
    """OWNER thêm user vào công trình; không cho thêm trùng."""
    get_site_or_404(db, site_id)
    require_owner(db, site_id, current_user)

    user = db.query(User).filter(User.id == member_in.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    if get_membership(db, site_id, user.id):
        raise HTTPException(status_code=400, detail="Người dùng đã là thành viên của công trình này")

    member = SiteMember(site_id=site_id, user_id=user.id, role=member_in.role)
    db.add(member)
    log_activity(
        db, current_user.id, site_id, "MEMBER_ADDED",
        f"Thêm thành viên user_id={user.id} với role={member_in.role.value}",
    )

    db.commit()
    db.refresh(member)
    return member


def remove_site_member(db: Session, site_id: int, user_id: int, current_user: User) -> None:
    """OWNER xóa member khỏi công trình; không được xóa OWNER cuối cùng."""
    get_site_or_404(db, site_id)
    require_owner(db, site_id, current_user)

    membership = get_membership(db, site_id, user_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Không tìm thấy thành viên trong công trình này")

    if membership.role == SiteMemberRole.OWNER:
        owner_count = (
            db.query(SiteMember)
            .filter(SiteMember.site_id == site_id, SiteMember.role == SiteMemberRole.OWNER)
            .count()
        )
        if owner_count <= 1:
            raise HTTPException(
                status_code=400, detail="Không thể xóa chủ sở hữu cuối cùng của công trình"
            )

    db.delete(membership)
    log_activity(db, current_user.id, site_id, "MEMBER_REMOVED", f"Xóa thành viên user_id={user_id}")

    db.commit()
