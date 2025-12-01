"""Organization context and multi-tenant dependencies."""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select

from api.dependencies.auth import CurrentUser
from core.database import DBSession
from core.exceptions import InvalidOrganizationContext, PermissionDenied
from models.organization_member import MemberRole, OrganizationMember


class OrgContext:
    """Organization context for multi-tenant operations."""

    def __init__(self, organization_id: int, user_id: int, role: MemberRole) -> None:
        self.organization_id = organization_id
        self.user_id = user_id
        self.role = role

    def is_owner(self) -> bool:
        """Check if user is owner."""
        result: bool = self.role == MemberRole.OWNER
        return result

    def is_admin(self) -> bool:
        """Check if user is admin."""
        result: bool = self.role == MemberRole.ADMIN
        return result

    def is_manager(self) -> bool:
        """Check if user is manager."""
        result: bool = self.role == MemberRole.MANAGER
        return result

    def is_member(self) -> bool:
        """Check if user is member."""
        result: bool = self.role == MemberRole.MEMBER
        return result

    def is_owner_or_admin(self) -> bool:
        """Check if user is owner or admin."""
        return self.role in (MemberRole.OWNER, MemberRole.ADMIN)

    def is_manager_or_above(self) -> bool:
        """Check if user is manager or above."""
        return self.role in (MemberRole.OWNER, MemberRole.ADMIN, MemberRole.MANAGER)


async def get_org_context(
    x_organization_id: Annotated[int | None, Header()] = None,
    current_user: CurrentUser = CurrentUser,
    db: DBSession = DBSession,
) -> OrgContext:
    """
    Get organization context from header and validate user membership.

    Args:
        x_organization_id: Organization ID from header
        current_user: Current authenticated user
        db: Database session

    Returns:
        Organization context with user's role

    Raises:
        InvalidOrganizationContext: If organization ID is missing
        PermissionDenied: If user is not a member of the organization
    """
    if not x_organization_id:
        raise InvalidOrganizationContext("X-Organization-Id header is required")

    # Check if user is a member of this organization
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == x_organization_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise PermissionDenied("You are not a member of this organization")

    return OrgContext(
        organization_id=x_organization_id, user_id=current_user.id, role=membership.role
    )


# Type alias for dependency injection
OrgContextDep = Annotated[OrgContext, Depends(get_org_context)]
