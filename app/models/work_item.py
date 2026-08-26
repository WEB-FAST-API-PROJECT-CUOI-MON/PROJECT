"""Bảng Hạng mục thi công, và các bảng con: comment (nhật ký thi công), attachment (file đính kèm)."""

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
    """Hạng mục thi công thuộc một công trình, được giao cho một đội thi công (Team)."""

    __tablename__ = "work_items"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("construction_sites.id"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    assignee_team_id = Column(
        Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    status = Column(Enum(WorkItemStatus), default=WorkItemStatus.TODO, nullable=False)
    priority = Column(Enum(WorkItemPriority), default=WorkItemPriority.MEDIUM, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    site = relationship("Site", back_populates="work_items")
    assignee_team = relationship("Team", back_populates="work_items")
    comments = relationship(
        "WorkItemComment",
        back_populates="work_item",
        cascade="all, delete-orphan",
        order_by="WorkItemComment.created_at",
    )
    attachments = relationship(
        "WorkItemAttachment",
        back_populates="work_item",
        cascade="all, delete-orphan",
        order_by="WorkItemAttachment.created_at",
    )


class WorkItemComment(Base):
    """Ghi chú / nhật ký thi công gắn với một hạng mục thi công."""

    __tablename__ = "work_item_comments"

    id = Column(Integer, primary_key=True, index=True)
    work_item_id = Column(Integer, ForeignKey("work_items.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    work_item = relationship("WorkItem", back_populates="comments")
    user = relationship("User")


class WorkItemAttachment(Base):
    """File đính kèm (hình ảnh / biên bản nghiệm thu) gắn với một hạng mục thi công.

    Chỉ lưu đường dẫn file trên đĩa (file_path), không lưu nội dung file trong DB.
    """

    __tablename__ = "work_item_attachments"

    id = Column(Integer, primary_key=True, index=True)
    work_item_id = Column(Integer, ForeignKey("work_items.id"), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    work_item = relationship("WorkItem", back_populates="attachments")
    uploaded_by = relationship("User")
