"""Organization routes."""

from fastapi import APIRouter, Path, status

from api.dependencies.auth import CurrentUser
from api.dependencies.organization import OrgContextDep
from core.database import DBSession
from schemas.organization import (
    MemberInvite,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationWithMembersResponse,
)
from services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization",
    description=(
        "Create a new organization. "
        "The creator automatically becomes the owner with full administrative privileges."
    ),
)
async def create_organization(
    data: OrganizationCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> OrganizationResponse:
    service = OrganizationService(db)
    org = await service.create_organization(data, current_user.id)
    return OrganizationResponse.model_validate(org)


@router.get(
    "",
    response_model=list[OrganizationResponse],
    summary="List user organizations",
    description="List all organizations where the current user is a member, regardless of role.",
)
@router.get(
    "/me",
    response_model=list[OrganizationResponse],
    summary="List user organizations",
    description="List all organizations where the current user is a member, regardless of role.",
)
async def list_organizations(
    current_user: CurrentUser, db: DBSession
) -> list[OrganizationResponse]:
    service = OrganizationService(db)
    orgs = await service.list_user_organizations(current_user.id)
    return [OrganizationResponse.model_validate(org) for org in orgs]


@router.get(
    "/{org_id}",
    response_model=OrganizationWithMembersResponse,
    summary="Get organization details",
    description=(
        "Retrieve detailed information about a specific organization "
        "including its member list with roles."
    ),
)
async def get_organization(
    *,
    org_id: int = Path(..., gt=0, description="Organization ID"),
    org_context: OrgContextDep,
    db: DBSession,
) -> OrganizationWithMembersResponse:
    service = OrganizationService(db)
    org = await service.get_organization_with_members(org_id)

    # Use schema's from_orm_member method for clean mapping
    from schemas.organization import MemberResponse

    return OrganizationWithMembersResponse(
        id=org.id,
        name=org.name,
        created_at=org.created_at,
        members=[MemberResponse.from_orm_member(m) for m in org.members],
    )


@router.post(
    "/{org_id}/members",
    status_code=status.HTTP_201_CREATED,
    summary="Invite member to organization",
    description=(
        "Invite a user to join the organization with a specific role. Requires owner or admin role."
    ),
)
async def invite_member(
    *,
    org_id: int = Path(..., gt=0, description="Organization ID"),
    data: MemberInvite,
    org_context: OrgContextDep,
    db: DBSession,
) -> dict:
    from models.types import AuthContext

    service = OrganizationService(db)

    # Convert HTTP context to domain AuthContext
    auth_context = AuthContext(
        user_id=org_context.user_id,
        organization_id=org_context.organization_id,
        role=org_context.role,
    )

    membership = await service.invite_member(org_id, data.user_id, data.role, auth_context)
    return {"message": "Member invited successfully", "membership_id": membership.id}


@router.patch(
    "/{org_id}/members/{user_id}",
    summary="Change member role",
    description="Update the role of an existing organization member. Requires owner or admin role.",
)
async def change_member_role(
    *,
    org_id: int = Path(..., gt=0, description="Organization ID"),
    user_id: int = Path(..., gt=0, description="User ID"),
    data: MemberInvite,
    org_context: OrgContextDep,
    db: DBSession,
) -> dict:
    from models.types import AuthContext

    service = OrganizationService(db)

    # Convert HTTP context to domain AuthContext
    auth_context = AuthContext(
        user_id=org_context.user_id,
        organization_id=org_context.organization_id,
        role=org_context.role,
    )

    await service.change_member_role(org_id, user_id, data.role, auth_context)
    return {"message": "Member role updated successfully"}


@router.delete(
    "/{org_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove member from organization",
    description="Remove a member from the organization. Requires owner or admin role.",
)
async def remove_member(
    *,
    org_id: int = Path(..., gt=0, description="Organization ID"),
    user_id: int = Path(..., gt=0, description="User ID"),
    org_context: OrgContextDep,
    db: DBSession,
) -> None:
    from models.types import AuthContext

    service = OrganizationService(db)

    # Convert HTTP context to domain AuthContext
    auth_context = AuthContext(
        user_id=org_context.user_id,
        organization_id=org_context.organization_id,
        role=org_context.role,
    )

    await service.remove_member(org_id, user_id, auth_context)
