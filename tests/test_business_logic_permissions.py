"""Unit tests for permission and role business rules."""

from models.organization_member import MemberRole
from models.types import AuthContext


class TestAuthContextPermissions:
    """Test AuthContext permission checking."""

    def test_owner_has_all_permissions(self):
        """Owner has all permissions."""
        auth = AuthContext(user_id=1, organization_id=1, role=MemberRole.OWNER)

        assert auth.is_owner()
        assert auth.is_owner_or_admin()
        assert auth.is_manager_or_above()
        assert not auth.is_member()

    def test_admin_has_admin_permissions(self):
        """Admin has admin permissions."""
        auth = AuthContext(user_id=1, organization_id=1, role=MemberRole.ADMIN)

        assert not auth.is_owner()
        assert auth.is_admin()
        assert auth.is_owner_or_admin()
        assert auth.is_manager_or_above()
        assert not auth.is_member()

    def test_manager_has_manager_permissions(self):
        """Manager has manager permissions."""
        auth = AuthContext(user_id=1, organization_id=1, role=MemberRole.MANAGER)

        assert not auth.is_owner()
        assert not auth.is_admin()
        assert not auth.is_owner_or_admin()
        assert auth.is_manager()
        assert auth.is_manager_or_above()
        assert not auth.is_member()

    def test_member_has_limited_permissions(self):
        """Member has limited permissions."""
        auth = AuthContext(user_id=1, organization_id=1, role=MemberRole.MEMBER)

        assert not auth.is_owner()
        assert not auth.is_admin()
        assert not auth.is_owner_or_admin()
        assert not auth.is_manager()
        assert not auth.is_manager_or_above()
        assert auth.is_member()


class TestResourceOwnershipRules:
    """Test resource ownership checking."""

    def test_owner_can_access_all_resources(self):
        """Owner can access all resources."""
        auth = AuthContext(user_id=1, organization_id=1, role=MemberRole.OWNER)

        assert auth.can_access_resource(1)  # Own resource
        assert auth.can_access_resource(999)  # Others' resources

    def test_admin_can_access_all_resources(self):
        """Admin can access all resources."""
        auth = AuthContext(user_id=1, organization_id=1, role=MemberRole.ADMIN)

        assert auth.can_access_resource(1)  # Own resource
        assert auth.can_access_resource(999)  # Others' resources

    def test_manager_can_access_all_resources(self):
        """Manager can access all resources."""
        auth = AuthContext(user_id=1, organization_id=1, role=MemberRole.MANAGER)

        assert auth.can_access_resource(1)  # Own resource
        assert auth.can_access_resource(999)  # Others' resources

    def test_member_can_only_access_own_resources(self):
        """Member can only access their own resources."""
        auth = AuthContext(user_id=1, organization_id=1, role=MemberRole.MEMBER)

        assert auth.can_access_resource(1)  # Own resource
        assert not auth.can_access_resource(2)  # Others' resources
        assert not auth.can_access_resource(999)  # Others' resources
