"""Organization repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.organization import Organization
from models.organization_member import MemberRole, OrganizationMember
from repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    """Repository for Organization operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Organization, db)

    async def create_organization(self, name: str, owner_id: int) -> Organization:
        """Create organization and add owner as member."""
        # Create organization
        org = await self.create(name=name)

        # Add owner as member
        membership = OrganizationMember(
            organization_id=org.id, user_id=owner_id, role=MemberRole.OWNER
        )
        self.db.add(membership)
        await self.db.flush()

        return org

    async def get_user_organizations(self, user_id: int) -> list[Organization]:
        """Get all organizations for a user."""
        result = await self.db.execute(
            select(Organization)
            .join(OrganizationMember)
            .where(OrganizationMember.user_id == user_id)
        )
        organizations: list[Organization] = list(result.scalars().all())
        return organizations

    async def get_with_members(self, org_id: int) -> Organization | None:
        """Get organization with members loaded."""
        result = await self.db.execute(
            select(Organization)
            .options(selectinload(Organization.members).selectinload(OrganizationMember.user))
            .where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_membership(self, organization_id: int, user_id: int) -> OrganizationMember | None:
        """Get membership for user in organization."""
        result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_member(
        self, organization_id: int, user_id: int, role: MemberRole
    ) -> OrganizationMember:
        """Add member to organization."""
        membership = OrganizationMember(organization_id=organization_id, user_id=user_id, role=role)
        self.db.add(membership)
        await self.db.flush()
        await self.db.refresh(membership)
        return membership

    async def update_member_role(
        self, membership: OrganizationMember, role: MemberRole
    ) -> OrganizationMember:
        """Update member role."""
        membership.role = role
        await self.db.flush()
        await self.db.refresh(membership)
        return membership

    async def remove_member(self, membership: OrganizationMember) -> None:
        """Remove member from organization."""
        await self.db.delete(membership)
        await self.db.flush()
