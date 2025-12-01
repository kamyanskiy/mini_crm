from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.activity import ActivityType


class ActivityCreate(BaseModel):
    type: ActivityType = ActivityType.COMMENT
    payload: dict = Field(default_factory=dict)


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deal_id: int
    author_id: int | None
    type: ActivityType
    payload: dict
    created_at: datetime
