from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserOut


class TeamBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    """Dùng cho PATCH — mọi field đều optional, chỉ field được gửi lên mới bị cập nhật."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class TeamOut(TeamBase):
    id: int
    site_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamMemberAdd(BaseModel):
    user_id: int


class TeamMemberOut(BaseModel):
    user_id: int
    joined_at: datetime
    user: UserOut

    model_config = ConfigDict(from_attributes=True)
