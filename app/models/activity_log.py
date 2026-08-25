"""Bảng Lịch sử thao tác (Activity log)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class ActivityLog(Base):
    """Ghi lại các thao tác quan trọng: tạo/sửa/xóa công trình, thêm/xóa thành viên,..."""

    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("construction_sites.id"), nullable=True)
    action = Column(String(50), nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
    site = relationship("Site")
