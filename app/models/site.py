"""Bảng Công trình / Thành viên."""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class SiteMemberRole(str, enum.Enum):
    OWNER = "OWNER"
    MEMBER = "MEMBER"


class Site(Base):
    """Công trình xây dựng."""

    __tablename__ = "construction_sites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Soft delete: xóa công trình không làm mất dữ liệu (work_items, activity_logs,...)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    members = relationship("SiteMember", back_populates="site", cascade="all, delete-orphan")
    work_items = relationship("WorkItem", back_populates="site", cascade="all, delete-orphan")


class SiteMember(Base):
    """Thành viên tham gia một công trình (liên kết User - Site, khóa chính kép)."""

    __tablename__ = "site_members"

    site_id = Column(Integer, ForeignKey("construction_sites.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role = Column(Enum(SiteMemberRole), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    site = relationship("Site", back_populates="members")
    user = relationship("User", back_populates="site_memberships")
