import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.work_item import WorkItemPriority, WorkItemStatus
from app.schemas.team import TeamOut
from app.schemas.user import UserOut


class WorkItemBase(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    assignee_team_id: int | None = None
    priority: WorkItemPriority = WorkItemPriority.MEDIUM
    due_date: datetime | None = None


class WorkItemCreate(WorkItemBase):
    pass


class WorkItemUpdate(BaseModel):
    """Dùng cho PATCH — mọi field đều optional, chỉ field được gửi lên mới bị cập nhật."""

    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    assignee_team_id: int | None = None
    status: WorkItemStatus | None = None
    priority: WorkItemPriority | None = None
    due_date: datetime | None = None


class WorkItemOut(BaseModel):
    id: int
    site_id: int
    title: str
    description: str | None
    assignee_team_id: int | None
    assignee_team: TeamOut | None = None
    status: WorkItemStatus
    priority: WorkItemPriority
    due_date: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkItemSortBy(str, enum.Enum):
    CREATED_AT = "created_at"
    DUE_DATE = "due_date"


class SortOrder(str, enum.Enum):
    ASC = "asc"
    DESC = "desc"


class WorkItemPage(BaseModel):
    """Kết quả phân trang: danh sách hạng mục + tổng số bản ghi khớp filter."""

    items: list[WorkItemOut]
    total: int
    page: int
    size: int


class WorkItemCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class WorkItemCommentOut(BaseModel):
    id: int
    work_item_id: int
    user_id: int
    content: str
    created_at: datetime
    user: UserOut

    model_config = ConfigDict(from_attributes=True)


class WorkItemAttachmentOut(BaseModel):
    id: int
    work_item_id: int
    uploaded_by_id: int
    file_name: str
    file_path: str
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
