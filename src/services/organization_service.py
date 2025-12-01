"""Organization service with business logic."""

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleViolation, PermissionDenied, ResourceNotFound
from models.organization import Organization
from models.organization_member import MemberRole, OrganizationMember
from models.types import AuthContext
from repositories.organization_repository import OrganizationRepository
from repositories.user_repository import UserRepository
from schemas.organization import OrganizationCreate


class OrganizationService:
    """Service for organization business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OrganizationRepository(db)
        self.user_repo = UserRepository(db)

    async def create_organization(self, data: OrganizationCreate, owner_id: int) -> Organization:
        """Create organization with owner as first member."""
        return await self.repo.create_organization(data.name, owner_id)

    async def get_organization(self, org_id: int) -> Organization:
        """Get organization by ID."""
        org = await self.repo.get_by_id(org_id)
        if not org:
            raise ResourceNotFound("Organization not found")
        return org

    async def get_organization_with_members(self, org_id: int) -> Organization:
        """Get organization with members."""
        org = await self.repo.get_with_members(org_id)
        if not org:
            raise ResourceNotFound("Organization not found")
        return org

    async def list_user_organizations(self, user_id: int) -> list[Organization]:
        """Get all organizations for a user."""
        organizations: list[Organization] = await self.repo.get_user_organizations(user_id)
        return organizations

    async def invite_member(
        self, org_id: int, user_id: int, role: MemberRole, auth_context: AuthContext
    ) -> OrganizationMember:
        """
        Invite a member to organization.

        Business Rule: Only owner/admin can invite members.
        """
        if not auth_context.is_owner_or_admin():
            raise PermissionDenied("Only owners and admins can invite members")

        # Check if user exists
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFound("User not found")

        # Check if already a member
        existing = await self.repo.get_membership(org_id, user_id)
        if existing:
            raise BusinessRuleViolation("User is already a member of this organization")

        return await self.repo.add_member(org_id, user_id, role)

    async def change_member_role(
        self,
        org_id: int,
        user_id: int,
        new_role: MemberRole,
        auth_context: AuthContext,
    ) -> OrganizationMember:
        """
        Change member role.

        Business Rule: Only owner/admin can change roles.
        """
        if not auth_context.is_owner_or_admin():
            raise PermissionDenied("Only owners and admins can change member roles")

        membership = await self.repo.get_membership(org_id, user_id)
        if not membership:
            raise ResourceNotFound("Member not found")

        # Cannot change own role
        if user_id == auth_context.user_id:
            raise BusinessRuleViolation("Cannot change your own role")

        return await self.repo.update_member_role(membership, new_role)

    async def remove_member(self, org_id: int, user_id: int, auth_context: AuthContext) -> None:
        """
        Remove member from organization.

        Business Rule: Only owner/admin can remove members.
        """
        if not auth_context.is_owner_or_admin():
            raise PermissionDenied("Only owners and admins can remove members")

        membership = await self.repo.get_membership(org_id, user_id)
        if not membership:
            raise ResourceNotFound("Member not found")

        # Cannot remove self
        if user_id == auth_context.user_id:
            raise BusinessRuleViolation("Cannot remove yourself from organization")

        await self.repo.remove_member(membership)
