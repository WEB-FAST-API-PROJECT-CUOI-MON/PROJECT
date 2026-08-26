"""Bảng Đội thi công (Tổ đội) và thành viên đội."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Team(Base):
    """Đội/tổ thi công, thuộc một công trình cụ thể. Hạng mục thi công được giao (assign)
    cho một đội chứ không giao trực tiếp cho một user."""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("construction_sites.id"), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    site = relationship("Site", back_populates="teams")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    work_items = relationship("WorkItem", back_populates="assignee_team")


class TeamMember(Base):
    """Thành viên (user) thuộc một đội thi công. User phải là thành viên của công trình
    trước khi được thêm vào đội."""

    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_member"),)

    team_id = Column(Integer, ForeignKey("teams.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    team = relationship("Team", back_populates="members")
    user = relationship("User")
