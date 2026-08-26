"""API cho Công trình."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.site import SiteCreate, SiteMemberAdd, SiteMemberOut, SiteOut, SiteUpdate
from app.services import site_service

router = APIRouter(prefix="/construction-sites", tags=["Construction Sites"])


# --- Công trình ---


@router.post(
    "",
    response_model=SiteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo công trình mới",
)
def create_site(
    site_in: SiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tạo công trình mới, người tạo tự động trở thành OWNER."""
    return site_service.create_site(db, site_in, current_user)


@router.get("", response_model=list[SiteOut], summary="Danh sách công trình của tôi")
def list_sites(
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách công trình mà user hiện tại là owner/member; hỗ trợ tìm theo tên."""
    return site_service.list_sites(db, current_user, search)


@router.get("/{site_id}", response_model=SiteOut, summary="Chi tiết công trình")
def get_site(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy chi tiết một công trình, chỉ thành viên công trình mới được xem."""
    return site_service.get_site_detail(db, site_id, current_user)


@router.put("/{site_id}", response_model=SiteOut, summary="Cập nhật công trình")
@router.patch("/{site_id}", response_model=SiteOut, summary="Cập nhật công trình")
def update_site(
    site_id: int,
    site_in: SiteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cập nhật công trình, chỉ OWNER được sửa."""
    return site_service.update_site(db, site_id, site_in, current_user)


@router.delete(
    "/{site_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Xóa công trình (soft delete)",
)
def delete_site(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xóa công trình (soft delete), chỉ OWNER được xóa."""
    site_service.delete_site(db, site_id, current_user)
    return None


# --- Thành viên công trình ---


@router.get("/{site_id}/members", response_model=list[SiteMemberOut], summary="Danh sách thành viên công trình")
def list_members(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Danh sách thành viên và role trong công trình."""
    return site_service.list_site_members(db, site_id, current_user)


@router.post(
    "/{site_id}/members",
    response_model=SiteMemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm thành viên vào công trình",
)
def add_member(
    site_id: int,
    member_in: SiteMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """OWNER thêm user vào công trình; không cho thêm trùng."""
    return site_service.add_site_member(db, site_id, member_in, current_user)


@router.delete(
    "/{site_id}/members/{user_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Xóa thành viên khỏi công trình",
)
def remove_member(
    site_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """OWNER xóa member khỏi công trình; không được xóa OWNER cuối cùng."""
    site_service.remove_site_member(db, site_id, user_id, current_user)
    return None
