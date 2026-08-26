"""Business logic cho Đội thi công (Tổ đội) và Thành viên đội."""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.team import TeamCreate, TeamMemberAdd, TeamUpdate
from app.utils.authz import get_membership, get_site_or_404, log_activity, require_member, require_owner


def get_team_or_404(db: Session, team_id: int) -> Team:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Không tìm thấy đội thi công")
    return team


def _get_team_membership(db: Session, team_id: int, user_id: int) -> TeamMember | None:
    return (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        .first()
    )


# --- Đội thi công ---


def create_team(db: Session, site_id: int, team_in: TeamCreate, current_user: User) -> Team:
    """Tạo đội thi công mới cho một công trình, chỉ OWNER được tạo."""
    get_site_or_404(db, site_id)
    require_owner(db, site_id, current_user)

    team = Team(**team_in.model_dump(), site_id=site_id)
    db.add(team)
    log_activity(db, current_user.id, site_id, "TEAM_CREATED", f"Tạo đội thi công '{team.name}'")

    db.commit()
    db.refresh(team)
    return team


def list_teams(db: Session, site_id: int, current_user: User) -> list[Team]:
    """Danh sách đội thi công thuộc một công trình."""
    get_site_or_404(db, site_id)
    require_member(db, site_id, current_user)
    return db.query(Team).filter(Team.site_id == site_id).order_by(Team.created_at.asc()).all()


def get_team_detail(db: Session, team_id: int, current_user: User) -> Team:
    """Chi tiết một đội thi công, chỉ thành viên công trình mới được xem."""
    team = get_team_or_404(db, team_id)
    require_member(db, team.site_id, current_user)
    return team


def update_team(db: Session, team_id: int, team_in: TeamUpdate, current_user: User) -> Team:
    """Cập nhật đội thi công, chỉ OWNER được sửa."""
    team = get_team_or_404(db, team_id)
    require_owner(db, team.site_id, current_user)

    data = team_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(team, field, value)

    log_activity(
        db, current_user.id, team.site_id, "TEAM_UPDATED", f"Cập nhật đội thi công: {sorted(data.keys())}"
    )

    db.commit()
    db.refresh(team)
    return team


def delete_team(db: Session, team_id: int, current_user: User) -> None:
    """Xóa đội thi công, chỉ OWNER được xóa. Hạng mục thi công đang giao cho đội sẽ về assignee_team_id=null."""
    team = get_team_or_404(db, team_id)
    require_owner(db, team.site_id, current_user)

    db.delete(team)
    log_activity(db, current_user.id, team.site_id, "TEAM_DELETED", f"Xóa đội thi công '{team.name}'")

    db.commit()


# --- Thành viên đội thi công ---


def list_team_members(db: Session, team_id: int, current_user: User) -> list[TeamMember]:
    """Danh sách thành viên trong đội thi công."""
    team = get_team_or_404(db, team_id)
    require_member(db, team.site_id, current_user)
    return (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .order_by(TeamMember.joined_at.asc())
        .all()
    )


def add_team_member(db: Session, team_id: int, member_in: TeamMemberAdd, current_user: User) -> TeamMember:
    """OWNER thêm một thành viên công trình vào đội thi công.

    Không cho thêm user chưa là thành viên của công trình, không cho thêm trùng.
    """
    team = get_team_or_404(db, team_id)
    require_owner(db, team.site_id, current_user)

    if not get_membership(db, team.site_id, member_in.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể thêm người đã là thành viên của công trình vào đội thi công",
        )

    if _get_team_membership(db, team_id, member_in.user_id):
        raise HTTPException(status_code=400, detail="Người dùng đã thuộc đội thi công này")

    member = TeamMember(team_id=team_id, user_id=member_in.user_id)
    db.add(member)
    log_activity(
        db, current_user.id, team.site_id, "TEAM_MEMBER_ADDED",
        f"Thêm user_id={member_in.user_id} vào đội '{team.name}'",
    )

    try:
        db.commit()
    except IntegrityError:
        # Hai request thêm cùng user_id gần như đồng thời đều pass qua check tồn tại ở trên
        # trước khi commit -> unique constraint (team_id, user_id) chặn ở DB, trả 400 thay vì 500.
        db.rollback()
        raise HTTPException(status_code=400, detail="Người dùng đã thuộc đội thi công này")

    db.refresh(member)
    return member


def remove_team_member(db: Session, team_id: int, user_id: int, current_user: User) -> None:
    """OWNER xóa thành viên khỏi đội thi công."""
    team = get_team_or_404(db, team_id)
    require_owner(db, team.site_id, current_user)

    membership = _get_team_membership(db, team_id, user_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Không tìm thấy thành viên trong đội thi công này")

    db.delete(membership)
    log_activity(
        db, current_user.id, team.site_id, "TEAM_MEMBER_REMOVED", f"Xóa user_id={user_id} khỏi đội '{team.name}'"
    )

    db.commit()
