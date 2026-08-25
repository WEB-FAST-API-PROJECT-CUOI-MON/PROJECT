"""Bảng Hạng mục thi công."""

import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class WorkItemStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class WorkItemPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class WorkItem(Base):
    """Hạng mục thi công thuộc một công trình."""

    __tablename__ = "work_items"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("construction_sites.id"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(WorkItemStatus), default=WorkItemStatus.TODO, nullable=False)
    priority = Column(Enum(WorkItemPriority), default=WorkItemPriority.MEDIUM, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    site = relationship("Site", back_populates="work_items")
    assignee = relationship("User")
