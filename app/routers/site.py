"""API cho Công trình."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.activity_log import ActivityLog
from app.models.site import Site, SiteMember, SiteMemberRole
from app.models.user import User
from app.schemas.site import SiteCreate, SiteMemberAdd, SiteMemberOut, SiteOut, SiteUpdate

router = APIRouter(prefix="/construction-sites", tags=["Construction Sites"])


# --- Helpers ---


def _get_site_or_404(db: Session, site_id: int) -> Site:
    site = db.query(Site).filter(Site.id == site_id, Site.is_deleted.is_(False)).first()
    if not site:
        raise HTTPException(status_code=404, detail="Không tìm thấy công trình")
    return site


def _get_membership(db: Session, site_id: int, user_id: int) -> SiteMember | None:
    return (
        db.query(SiteMember)
        .filter(SiteMember.site_id == site_id, SiteMember.user_id == user_id)
        .first()
    )


def _require_member(db: Session, site_id: int, current_user: User) -> SiteMember:
    membership = _get_membership(db, site_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không phải thành viên của công trình này",
        )
    return membership


def _require_owner(db: Session, site_id: int, current_user: User) -> SiteMember:
    membership = _require_member(db, site_id, current_user)
    if membership.role != SiteMemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ chủ sở hữu công trình mới được thực hiện hành động này",
        )
    return membership


def _log(db: Session, user_id: int, site_id: int | None, action: str, detail: str | None = None) -> None:
    db.add(ActivityLog(user_id=user_id, site_id=site_id, action=action, detail=detail))


# --- Công trình ---


@router.post("", response_model=SiteOut, status_code=status.HTTP_201_CREATED)
def create_site(
    site_in: SiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tạo công trình mới, người tạo tự động trở thành OWNER."""
    site = Site(**site_in.model_dump(), owner_id=current_user.id)
    db.add(site)
    db.flush()  # cần site.id trước khi tạo SiteMember

    db.add(SiteMember(site_id=site.id, user_id=current_user.id, role=SiteMemberRole.OWNER))
    _log(db, current_user.id, site.id, "SITE_CREATED", f"Tạo công trình '{site.name}'")

    db.commit()
    db.refresh(site)
    return site


@router.get("", response_model=list[SiteOut])
def list_sites(
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách công trình mà user hiện tại là owner/member; hỗ trợ tìm theo tên."""
    query = (
        db.query(Site)
        .join(SiteMember, SiteMember.site_id == Site.id)
        .filter(SiteMember.user_id == current_user.id, Site.is_deleted.is_(False))
    )
    if search:
        query = query.filter(Site.name.ilike(f"%{search}%"))
    return query.order_by(Site.created_at.desc()).all()


@router.get("/{site_id}", response_model=SiteOut)
def get_site(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy chi tiết một công trình, chỉ thành viên công trình mới được xem."""
    site = _get_site_or_404(db, site_id)
    _require_member(db, site_id, current_user)
    return site


@router.put("/{site_id}", response_model=SiteOut)
@router.patch("/{site_id}", response_model=SiteOut)
def update_site(
    site_id: int,
    site_in: SiteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cập nhật công trình, chỉ OWNER được sửa."""
    site = _get_site_or_404(db, site_id)
    _require_owner(db, site_id, current_user)

    data = site_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(site, field, value)

    _log(db, current_user.id, site.id, "SITE_UPDATED", f"Cập nhật công trình: {sorted(data.keys())}")

    db.commit()
    db.refresh(site)
    return site


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xóa công trình (soft delete), chỉ OWNER được xóa."""
    site = _get_site_or_404(db, site_id)
    _require_owner(db, site_id, current_user)

    site.is_deleted = True
    site.deleted_at = func.now()
    _log(db, current_user.id, site.id, "SITE_DELETED", f"Xóa công trình '{site.name}'")

    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Thành viên công trình ---


@router.get("/{site_id}/members", response_model=list[SiteMemberOut])
def list_members(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Danh sách thành viên và role trong công trình."""
    _get_site_or_404(db, site_id)
    _require_member(db, site_id, current_user)
    return (
        db.query(SiteMember)
        .filter(SiteMember.site_id == site_id)
        .order_by(SiteMember.joined_at.asc())
        .all()
    )


@router.post("/{site_id}/members", response_model=SiteMemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    site_id: int,
    member_in: SiteMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """OWNER thêm user vào công trình; không cho thêm trùng."""
    _get_site_or_404(db, site_id)
    _require_owner(db, site_id, current_user)

    user = db.query(User).filter(User.id == member_in.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    if _get_membership(db, site_id, user.id):
        raise HTTPException(status_code=400, detail="Người dùng đã là thành viên của công trình này")

    member = SiteMember(site_id=site_id, user_id=user.id, role=member_in.role)
    db.add(member)
    _log(
        db, current_user.id, site_id, "MEMBER_ADDED",
        f"Thêm thành viên user_id={user.id} với role={member_in.role.value}",
    )

    db.commit()
    db.refresh(member)
    return member


@router.delete("/{site_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    site_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """OWNER xóa member khỏi công trình; không được xóa OWNER cuối cùng."""
    _get_site_or_404(db, site_id)
    _require_owner(db, site_id, current_user)

    membership = _get_membership(db, site_id, user_id)
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
    _log(db, current_user.id, site_id, "MEMBER_REMOVED", f"Xóa thành viên user_id={user_id}")

    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
