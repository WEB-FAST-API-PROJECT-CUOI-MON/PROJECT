"""API cho Hạng mục thi công."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.work_item import WorkItem
from app.schemas.work_item import WorkItemCreate, WorkItemOut

router = APIRouter(prefix="/construction-sites/{site_id}/work-items", tags=["Work Items"])


@router.post("", response_model=WorkItemOut, status_code=status.HTTP_201_CREATED)
def create_work_item(
    site_id: int,
    item_in: WorkItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tạo hạng mục thi công mới cho một công trình."""
    item = WorkItem(**item_in.model_dump(), site_id=site_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[WorkItemOut])
def list_work_items(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách hạng mục thi công của một công trình."""
    return db.query(WorkItem).filter(WorkItem.site_id == site_id).all()


@router.get("/{item_id}", response_model=WorkItemOut)
def get_work_item(
    site_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy chi tiết một hạng mục thi công."""
    item = (
        db.query(WorkItem)
        .filter(WorkItem.id == item_id, WorkItem.site_id == site_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy hạng mục thi công")
    return item
