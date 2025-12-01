from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date_not_past(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            # Check if due_date is in the past (before today)
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if v < today_start:
                raise ValueError("due_date cannot be in the past")
        return v


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    due_date: datetime | None = None
    is_done: bool | None = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date_not_past(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if v < today_start:
                raise ValueError("due_date cannot be in the past")
        return v


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deal_id: int
    title: str
    description: str | None
    due_date: datetime | None
    is_done: bool
    created_at: datetime
