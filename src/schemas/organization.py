from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from models.organization_member import MemberRole

if TYPE_CHECKING:
    pass


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class MemberInvite(BaseModel):
    user_id: int
    role: MemberRole


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    role: MemberRole
    user_name: str | None = None
    user_email: str | None = None

    @classmethod
    def from_orm_member(cls, member: Any) -> "MemberResponse":
        """
        Create MemberResponse from OrganizationMember ORM object.

        Args:
            member: OrganizationMember ORM object with user relationship loaded

        Returns:
            MemberResponse with user details
        """
        return cls(
            id=member.id,
            user_id=member.user_id,
            role=member.role,
            user_name=member.user.name if member.user else None,
            user_email=member.user.email if member.user else None,
        )


class OrganizationWithMembersResponse(OrganizationResponse):
    members: list[MemberResponse] = []
