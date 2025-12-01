import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.deal import Deal
    from models.user import User


class ActivityType(str, enum.Enum):
    COMMENT = "comment"
    STATUS_CHANGED = "status_changed"
    STAGE_CHANGED = "stage_changed"
    TASK_CREATED = "task_created"
    SYSTEM = "system"


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[ActivityType]
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    deal: Mapped["Deal"] = relationship(back_populates="activities")
    author: Mapped["User | None"] = relationship(back_populates="activities")
