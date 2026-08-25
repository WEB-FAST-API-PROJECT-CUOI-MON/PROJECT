from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.work_item import WorkItemPriority, WorkItemStatus


class WorkItemBase(BaseModel):
    title: str
    description: str | None = None
    assignee_id: int | None = None
    priority: WorkItemPriority = WorkItemPriority.MEDIUM
    due_date: datetime | None = None


class WorkItemCreate(WorkItemBase):
    pass


class WorkItemOut(WorkItemBase):
    id: int
    site_id: int
    status: WorkItemStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
