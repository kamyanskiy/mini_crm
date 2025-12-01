"""Permission checking utilities."""

from api.dependencies.organization import OrgContext
from core.exceptions import PermissionDenied


def require_owner_or_admin(org_context: OrgContext) -> None:
    """
    Require user to be owner or admin.

    Args:
        org_context: Organization context

    Raises:
        PermissionDenied: If user is not owner or admin
    """
    if not org_context.is_owner_or_admin():
        raise PermissionDenied("Only owners and admins can perform this action")


def require_manager_or_above(org_context: OrgContext) -> None:
    """
    Require user to be manager or above.

    Args:
        org_context: Organization context

    Raises:
        PermissionDenied: If user is member (not manager or above)
    """
    if not org_context.is_manager_or_above():
        raise PermissionDenied("Insufficient permissions")


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
