import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.activity import Activity
    from models.contact import Contact
    from models.organization import Organization
    from models.task import Task
    from models.user import User


class DealStatus(str, enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    WON = "won"
    LOST = "lost"


class DealStage(str, enum.Enum):
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED = "closed"


# Stage order for validation
STAGE_ORDER = {
    DealStage.QUALIFICATION: 1,
    DealStage.PROPOSAL: 2,
    DealStage.NEGOTIATION: 3,
    DealStage.CLOSED: 4,
}


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str]
    amount: Mapped[Decimal] = mapped_column(Numeric[Decimal](12, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(default="USD")
    status: Mapped[DealStatus] = mapped_column(default=DealStatus.NEW)
    stage: Mapped[DealStage] = mapped_column(default=DealStage.QUALIFICATION)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="deals")
    contact: Mapped["Contact | None"] = relationship(back_populates="deals")
    owner: Mapped["User"] = relationship(back_populates="owned_deals")
    tasks: Mapped[list["Task"]] = relationship(back_populates="deal", cascade="all, delete-orphan")
    activities: Mapped[list["Activity"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan"
    )
