from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.site import SiteMemberRole
from app.schemas.user import UserOut


class SiteBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    """Dùng cho cả PUT/PATCH — mọi field đều optional, chỉ field được gửi lên mới bị cập nhật."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class SiteOut(SiteBase):
    id: int
    owner_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SiteMemberAdd(BaseModel):
    user_id: int
    role: SiteMemberRole = SiteMemberRole.MEMBER


class SiteMemberOut(BaseModel):
 3   user_id: int
    role: SiteMemberRole
    joined_at: datetime
    user: UserOut

    model_config = ConfigDict(from_attributes=True)
