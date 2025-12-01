from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.activity import Activity
    from models.contact import Contact
    from models.deal import Deal
    from models.organization_member import OrganizationMember


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    name: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    memberships: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    owned_contacts: Mapped[list["Contact"]] = relationship(
        back_populates="owner", foreign_keys="Contact.owner_id"
    )
    owned_deals: Mapped[list["Deal"]] = relationship(
        back_populates="owner", foreign_keys="Deal.owner_id"
    )
    activities: Mapped[list["Activity"]] = relationship(back_populates="author")
