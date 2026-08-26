"""API cho Hạng mục thi công (work item) và các tính năng nâng cao: comment, attachment.

Permission matrix:
- OWNER công trình: toàn quyền trên mọi hạng mục thi công của công trình (tạo/sửa mọi field/xóa/assign).
- MEMBER công trình: được xem tất cả, được tạo hạng mục thi công mới.
- MEMBER thuộc đội (team) đang được assign hạng mục ("assignee"): được cập nhật status/description
  của hạng mục đó (ghi nhận tiến độ), nhưng không được đổi title/priority/due_date/assignee_team_id,
  không được xóa.
- MEMBER không liên quan (không phải OWNER, không thuộc đội được assign): chỉ được xem, không được sửa/xóa.
"""

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.work_item import WorkItemPriority, WorkItemStatus
from app.schemas.work_item import (
    SortOrder,
    WorkItemAttachmentOut,
    WorkItemCommentCreate,
    WorkItemCommentOut,
    WorkItemCreate,
    WorkItemOut,
    WorkItemPage,
    WorkItemSortBy,
    WorkItemUpdate,
)
from app.services import work_item_service

router = APIRouter(tags=["Work Items"])


# --- Hạng mục thi công ---


@router.post(
    "/construction-sites/{site_id}/work-items",
    response_model=WorkItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo hạng mục thi công",
)
def create_work_item(
    site_id: int,
    item_in: WorkItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tạo hạng mục thi công mới cho một công trình. Mọi thành viên công trình đều có quyền tạo."""
    return work_item_service.create_work_item(db, site_id, item_in, current_user)


@router.get(
    "/construction-sites/{site_id}/work-items",
    response_model=WorkItemPage,
    summary="Danh sách hạng mục thi công (filter/search/sort/pagination)",
)
def list_work_items(
    site_id: int,
    status_filter: WorkItemStatus | None = Query(default=None, alias="status"),
    priority: WorkItemPriority | None = None,
    assignee_team_id: int | None = None,
    search: str | None = Query(default=None, description="Tìm theo title"),
    sort_by: WorkItemSortBy = WorkItemSortBy.CREATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Danh sách hạng mục thi công thuộc một công trình, hỗ trợ filter/search/pagination/sort.

    Chỉ trả hạng mục thuộc đúng công trình này, không lộ hạng mục của công trình khác.
    """
    return work_item_service.list_work_items(
        db, site_id, current_user, status_filter, priority, assignee_team_id,
        search, sort_by, sort_order, page, size,
    )


@router.get("/work-items/{item_id}", response_model=WorkItemOut, summary="Chi tiết hạng mục thi công")
def get_work_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Chi tiết một hạng mục thi công. Kiểm tra user thuộc công trình trước khi trả dữ liệu."""
    return work_item_service.get_work_item_detail(db, item_id, current_user)


@router.patch("/work-items/{item_id}", response_model=WorkItemOut, summary="Cập nhật hạng mục thi công")
def update_work_item(
    item_id: int,
    item_in: WorkItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cập nhật hạng mục thi công — chỉ field được gửi lên mới bị ghi đè.

    OWNER công trình: sửa được mọi field.
    Thành viên thuộc đội đang được assign hạng mục: chỉ được sửa status/description (cập nhật tiến độ).
    """
    return work_item_service.update_work_item(db, item_id, item_in, current_user)


@router.delete(
    "/work-items/{item_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Xóa hạng mục thi công",
)
def delete_work_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xóa hạng mục thi công, chỉ OWNER công trình được xóa."""
    work_item_service.delete_work_item(db, item_id, current_user)
    return None


# --- Comment (nhật ký thi công) ---


@router.get(
    "/work-items/{item_id}/comments",
    response_model=list[WorkItemCommentOut],
    summary="Danh sách comment (nhật ký thi công)",
)
def list_work_item_comments(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Danh sách comment của một hạng mục thi công. Chỉ thành viên công trình được xem."""
    return work_item_service.list_work_item_comments(db, item_id, current_user)


@router.post(
    "/work-items/{item_id}/comments",
    response_model=WorkItemCommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm comment",
)
def create_work_item_comment(
    item_id: int,
    comment_in: WorkItemCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Thêm comment (ghi chú nhật ký thi công) cho hạng mục. Chỉ thành viên công trình được tạo."""
    return work_item_service.create_work_item_comment(db, item_id, comment_in, current_user)


# --- Attachment (file đính kèm) ---


@router.get(
    "/work-items/{item_id}/attachments",
    response_model=list[WorkItemAttachmentOut],
    summary="Danh sách file đính kèm",
)
def list_work_item_attachments(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Danh sách file đính kèm của một hạng mục thi công. Chỉ thành viên công trình được xem."""
    return work_item_service.list_work_item_attachments(db, item_id, current_user)


@router.post(
    "/work-items/{item_id}/attachments",
    response_model=WorkItemAttachmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file đính kèm",
)
async def upload_work_item_attachment(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload file đính kèm (hình ảnh/biên bản nghiệm thu) cho hạng mục thi công.

    Kiểm tra loại file (chỉ ảnh jpg/png/webp hoặc pdf) và kích thước (tối đa
    settings.WORK_ITEM_ATTACHMENT_MAX_SIZE_MB), lưu file vào đĩa và lưu đường dẫn trong DB.
    """
    return await work_item_service.upload_work_item_attachment(db, item_id, file, current_user)
