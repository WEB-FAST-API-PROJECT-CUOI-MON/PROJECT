"""API cho Đội thi công (Tổ đội).

Hạng mục thi công được giao (assign) cho một đội thi công thuộc công trình, chứ không giao
trực tiếp cho một user — do đó cần API quản lý đội và thành viên đội trước khi có thể assign.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.team import TeamCreate, TeamMemberAdd, TeamMemberOut, TeamOut, TeamUpdate
from app.services import team_service

router = APIRouter(tags=["Teams"])


# --- Đội thi công ---


@router.post(
    "/construction-sites/{site_id}/teams",
    response_model=TeamOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo đội thi công",
)
def create_team(
    site_id: int,
    team_in: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tạo đội thi công mới cho một công trình, chỉ OWNER được tạo."""
    return team_service.create_team(db, site_id, team_in, current_user)


@router.get("/construction-sites/{site_id}/teams", response_model=list[TeamOut], summary="Danh sách đội thi công")
def list_teams(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Danh sách đội thi công thuộc một công trình."""
    return team_service.list_teams(db, site_id, current_user)


@router.get("/teams/{team_id}", response_model=TeamOut, summary="Chi tiết đội thi công")
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Chi tiết một đội thi công, chỉ thành viên công trình mới được xem."""
    return team_service.get_team_detail(db, team_id, current_user)


@router.patch("/teams/{team_id}", response_model=TeamOut, summary="Cập nhật đội thi công")
def update_team(
    team_id: int,
    team_in: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cập nhật đội thi công, chỉ OWNER được sửa."""
    return team_service.update_team(db, team_id, team_in, current_user)


@router.delete(
    "/teams/{team_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Xóa đội thi công",
)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xóa đội thi công, chỉ OWNER được xóa. Hạng mục thi công đang giao cho đội sẽ về assignee_team_id=null."""
    team_service.delete_team(db, team_id, current_user)
    return None


# --- Thành viên đội thi công ---


@router.get("/teams/{team_id}/members", response_model=list[TeamMemberOut], summary="Danh sách thành viên đội")
def list_team_members(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Danh sách thành viên trong đội thi công."""
    return team_service.list_team_members(db, team_id, current_user)


@router.post(
    "/teams/{team_id}/members",
    response_model=TeamMemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm thành viên vào đội thi công",
)
def add_team_member(
    team_id: int,
    member_in: TeamMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """OWNER thêm một thành viên công trình vào đội thi công.

    Không cho thêm user chưa là thành viên của công trình, không cho thêm trùng.
    """
    return team_service.add_team_member(db, team_id, member_in, current_user)


@router.delete(
    "/teams/{team_id}/members/{user_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Xóa thành viên khỏi đội thi công",
)
def remove_team_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """OWNER xóa thành viên khỏi đội thi công."""
    team_service.remove_team_member(db, team_id, user_id, current_user)
    return None
