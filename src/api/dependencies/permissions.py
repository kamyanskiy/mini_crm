"""Permission checking utilities."""

from api.dependencies.organization import OrgContext
from core.exceptions import PermissionDenied


def check_resource_ownership(org_context: OrgContext, resource_owner_id: int) -> None:
    """
    Check if user owns the resource. For members, they can only access their own resources.

    Args:
        org_context: Organization context
        resource_owner_id: Owner ID of the resource

    Raises:
        PermissionDenied: If member tries to access others' resources
    """
    # Owner, admin, and manager can access all resources
    if org_context.is_manager_or_above():
        return

    # Members can only access their own resources
    if org_context.user_id != resource_owner_id:
        raise PermissionDenied("You can only access your own resources")
