"""Domain types and value objects."""

from dataclasses import dataclass

from models.organization_member import MemberRole


@dataclass
class AuthContext:
    """
    Domain object for authorization context.

    This is a clean domain object that doesn't depend on HTTP layer.
    Services can use this instead of OrgContext (HTTP dependency).
    """

    user_id: int
    organization_id: int
    role: MemberRole

    def is_owner(self) -> bool:
        """Check if user is organization owner."""
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
        """Check if user is regular member."""
        result: bool = self.role == MemberRole.MEMBER
        return result

    def is_owner_or_admin(self) -> bool:
        """Check if user has owner or admin privileges."""
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN]

    def is_manager_or_above(self) -> bool:
        """Check if user has manager privileges or above."""
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.MANAGER]

    def can_access_resource(self, resource_owner_id: int) -> bool:
        """
        Check if user can access a resource.

        Manager and above can access all resources.
        Members can only access their own resources.
        """
        if self.is_manager_or_above():
            return True
        return self.user_id == resource_owner_id
