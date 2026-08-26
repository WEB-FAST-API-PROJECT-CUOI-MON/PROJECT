"""Business logic cho Hạng mục thi công (work item) và các tính năng nâng cao: comment, attachment.

Permission matrix:
- OWNER công trình: toàn quyền trên mọi hạng mục thi công của công trình (tạo/sửa mọi field/xóa/assign).
- MEMBER công trình: được xem tất cả, được tạo hạng mục thi công mới.
- MEMBER thuộc đội (team) đang được assign hạng mục ("assignee"): được cập nhật status/description
  của hạng mục đó (ghi nhận tiến độ), nhưng không được đổi title/priority/due_date/assignee_team_id,
  không được xóa.
- MEMBER không liên quan (không phải OWNER, không thuộc đội được assign): chỉ được xem, không được sửa/xóa.
"""

import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.site import SiteMemberRole
from app.models.team import Team, TeamMember
from app.models.user import User
from app.models.work_item import WorkItem, WorkItemAttachment, WorkItemComment, WorkItemPriority, WorkItemStatus
from app.schemas.work_item import (
    SortOrder,
    WorkItemCommentCreate,
    WorkItemCreate,
    WorkItemPage,
    WorkItemSortBy,
    WorkItemUpdate,
)
from app.utils.authz import get_site_or_404, log_activity, require_member

# Chỉ chấp nhận hình ảnh (chụp hiện trường) và PDF (biên bản nghiệm thu)
ALLOWED_ATTACHMENT_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
ALLOWED_ATTACHMENT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}

# Đọc file upload theo từng chunk 1MB thay vì load nguyên file vào RAM một lần.
_UPLOAD_CHUNK_SIZE = 1024 * 1024


# --- Helpers ---


def get_work_item_or_404(db: Session, item_id: int) -> WorkItem:
    item = db.query(WorkItem).filter(WorkItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy hạng mục thi công")
    return item


def _get_team_or_404_in_site(db: Session, team_id: int, site_id: int) -> Team:
    team = db.query(Team).filter(Team.id == team_id, Team.site_id == site_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đội thi công không tồn tại hoặc không thuộc công trình này",
        )
    return team


def _is_team_member(db: Session, team_id: int | None, user_id: int) -> bool:
    if team_id is None:
        return False
    return (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        .first()
        is not None
    )


# --- Hạng mục thi công ---


def create_work_item(db: Session, site_id: int, item_in: WorkItemCreate, current_user: User) -> WorkItem:
    """Tạo hạng mục thi công mới cho một công trình. Mọi thành viên công trình đều có quyền tạo."""
    get_site_or_404(db, site_id)
    require_member(db, site_id, current_user)

    if item_in.assignee_team_id is not None:
        _get_team_or_404_in_site(db, item_in.assignee_team_id, site_id)

    item = WorkItem(**item_in.model_dump(), site_id=site_id)
    db.add(item)
    log_activity(db, current_user.id, site_id, "WORK_ITEM_CREATED", f"Tạo hạng mục '{item.title}'")

    db.commit()
    db.refresh(item)
    return item


def list_work_items(
    db: Session,
    site_id: int,
    current_user: User,
    status_filter: WorkItemStatus | None,
    priority: WorkItemPriority | None,
    assignee_team_id: int | None,
    search: str | None,
    sort_by: WorkItemSortBy,
    sort_order: SortOrder,
    page: int,
    size: int,
) -> WorkItemPage:
    """Danh sách hạng mục thi công thuộc một công trình, hỗ trợ filter/search/pagination/sort.

    Chỉ trả hạng mục thuộc đúng công trình này, không lộ hạng mục của công trình khác.
    """
    get_site_or_404(db, site_id)
    require_member(db, site_id, current_user)

    query = db.query(WorkItem).filter(WorkItem.site_id == site_id)
    if status_filter is not None:
        query = query.filter(WorkItem.status == status_filter)
    if priority is not None:
        query = query.filter(WorkItem.priority == priority)
    if assignee_team_id is not None:
        query = query.filter(WorkItem.assignee_team_id == assignee_team_id)
    if search:
        query = query.filter(WorkItem.title.ilike(f"%{search}%"))

    total = query.count()

    sort_column = WorkItem.created_at if sort_by == WorkItemSortBy.CREATED_AT else WorkItem.due_date
    sort_column = sort_column.asc() if sort_order == SortOrder.ASC else sort_column.desc()

    # joinedload assignee_team để serialize WorkItemOut.assignee_team không phát sinh
    # thêm 1 query SELECT teams... cho mỗi item (N+1) — chỉ áp dụng cho trang kết quả
    # cuối cùng, không áp dụng cho query .count() ở trên.
    items = (
        query.options(joinedload(WorkItem.assignee_team))
        .order_by(sort_column)
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return WorkItemPage(items=items, total=total, page=page, size=size)


def get_work_item_detail(db: Session, item_id: int, current_user: User) -> WorkItem:
    """Chi tiết một hạng mục thi công. Kiểm tra user thuộc công trình trước khi trả dữ liệu."""
    item = get_work_item_or_404(db, item_id)
    require_member(db, item.site_id, current_user)
    return item


def update_work_item(db: Session, item_id: int, item_in: WorkItemUpdate, current_user: User) -> WorkItem:
    """Cập nhật hạng mục thi công — chỉ field được gửi lên mới bị ghi đè.

    OWNER công trình: sửa được mọi field.
    Thành viên thuộc đội đang được assign hạng mục: chỉ được sửa status/description (cập nhật tiến độ).
    """
    item = get_work_item_or_404(db, item_id)
    membership = require_member(db, item.site_id, current_user)

    data = item_in.model_dump(exclude_unset=True)

    if membership.role != SiteMemberRole.OWNER:
        if not _is_team_member(db, item.assignee_team_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền cập nhật hạng mục thi công này",
            )
        allowed_fields = {"status", "description"}
        if not set(data.keys()) <= allowed_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ chủ sở hữu công trình mới được sửa title/priority/due_date/assignee_team_id",
            )

    if "assignee_team_id" in data and data["assignee_team_id"] is not None:
        _get_team_or_404_in_site(db, data["assignee_team_id"], item.site_id)

    for field, value in data.items():
        setattr(item, field, value)

    log_activity(
        db, current_user.id, item.site_id, "WORK_ITEM_UPDATED", f"Cập nhật hạng mục '{item.title}': {sorted(data.keys())}"
    )

    db.commit()
    db.refresh(item)
    return item


def delete_work_item(db: Session, item_id: int, current_user: User) -> None:
    """Xóa hạng mục thi công, chỉ OWNER công trình được xóa."""
    item = get_work_item_or_404(db, item_id)
    membership = require_member(db, item.site_id, current_user)
    if membership.role != SiteMemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ chủ sở hữu công trình mới được xóa hạng mục thi công",
        )

    # Lưu lại đường dẫn file đính kèm trước khi xóa record (cascade delete-orphan sẽ xóa
    # luôn các dòng WorkItemAttachment trong DB) để dọn file vật lý trên đĩa sau khi commit.
    attachment_paths = [a.file_path for a in item.attachments]

    db.delete(item)
    log_activity(db, current_user.id, item.site_id, "WORK_ITEM_DELETED", f"Xóa hạng mục '{item.title}'")

    db.commit()

    for path in attachment_paths:
        try:
            os.remove(path)
        except OSError:
            pass  # File đã bị xóa/di chuyển thủ công từ trước -> bỏ qua, không chặn việc xóa hạng mục.


# --- Comment (nhật ký thi công) ---


def list_work_item_comments(db: Session, item_id: int, current_user: User) -> list[WorkItemComment]:
    """Danh sách comment của một hạng mục thi công. Chỉ thành viên công trình được xem."""
    item = get_work_item_or_404(db, item_id)
    require_member(db, item.site_id, current_user)
    return (
        db.query(WorkItemComment)
        .options(joinedload(WorkItemComment.user))  # tránh N+1 khi serialize WorkItemCommentOut.user
        .filter(WorkItemComment.work_item_id == item_id)
        .order_by(WorkItemComment.created_at.asc())
        .all()
    )


def create_work_item_comment(
    db: Session, item_id: int, comment_in: WorkItemCommentCreate, current_user: User
) -> WorkItemComment:
    """Thêm comment (ghi chú nhật ký thi công) cho hạng mục. Chỉ thành viên công trình được tạo."""
    item = get_work_item_or_404(db, item_id)
    require_member(db, item.site_id, current_user)

    comment = WorkItemComment(work_item_id=item_id, user_id=current_user.id, content=comment_in.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


# --- Attachment (file đính kèm) ---


def list_work_item_attachments(db: Session, item_id: int, current_user: User) -> list[WorkItemAttachment]:
    """Danh sách file đính kèm của một hạng mục thi công. Chỉ thành viên công trình được xem."""
    item = get_work_item_or_404(db, item_id)
    require_member(db, item.site_id, current_user)
    return (
        db.query(WorkItemAttachment)
        .filter(WorkItemAttachment.work_item_id == item_id)
        .order_by(WorkItemAttachment.created_at.asc())
        .all()
    )


async def upload_work_item_attachment(
    db: Session, item_id: int, file: UploadFile, current_user: User
) -> WorkItemAttachment:
    """Upload file đính kèm (hình ảnh/biên bản nghiệm thu) cho hạng mục thi công.

    Kiểm tra loại file (chỉ ảnh jpg/png/webp hoặc pdf) và kích thước (tối đa
    settings.WORK_ITEM_ATTACHMENT_MAX_SIZE_MB), lưu file vào đĩa và lưu đường dẫn trong DB.
    """
    item = get_work_item_or_404(db, item_id)
    require_member(db, item.site_id, current_user)

    original_name = file.filename or ""
    extension = os.path.splitext(original_name)[1].lower()
    if file.content_type not in ALLOWED_ATTACHMENT_CONTENT_TYPES or extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loại file không được hỗ trợ, chỉ chấp nhận ảnh (jpg/png/webp) hoặc PDF",
        )

    # Đọc theo từng chunk và chặn sớm ngay khi vượt kích thước tối đa, tránh phải buffer
    # toàn bộ file (có thể rất lớn) vào RAM trước khi biết nó có hợp lệ hay không.
    max_size_bytes = settings.WORK_ITEM_ATTACHMENT_MAX_SIZE_MB * 1024 * 1024
    content = bytearray()
    while chunk := await file.read(_UPLOAD_CHUNK_SIZE):
        content.extend(chunk)
        if len(content) > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File vượt quá kích thước tối đa {settings.WORK_ITEM_ATTACHMENT_MAX_SIZE_MB}MB",
            )
    content = bytes(content)

    item_dir = os.path.join(settings.WORK_ITEM_UPLOAD_DIR, str(item_id))
    os.makedirs(item_dir, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(item_dir, stored_name)
    with open(file_path, "wb") as f:
        f.write(content)

    attachment = WorkItemAttachment(
        work_item_id=item_id,
        uploaded_by_id=current_user.id,
        file_name=original_name,
        file_path=file_path.replace(os.sep, "/"),
        content_type=file.content_type,
        size_bytes=len(content),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment
