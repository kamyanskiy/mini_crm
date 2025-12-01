"""Contact routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from api.dependencies.organization import OrgContextDep
from api.dependencies.pagination import PaginationParams
from api.dependencies.permissions import check_resource_ownership
from core.database import DBSession
from schemas.contact import ContactCreate, ContactResponse, ContactUpdate
from services.contact_service import ContactService

PaginationDep = Annotated[PaginationParams, Depends()]

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get(
    "",
    response_model=list[ContactResponse],
    summary="List contacts",
)
async def list_contacts(
    org_context: OrgContextDep,
    db: DBSession,
    pagination: PaginationDep,
    search: str | None = Query(None, max_length=255, description="Search by name or email"),
    owner_id: int | None = Query(None, gt=0, description="Filter by owner ID"),
) -> list[ContactResponse]:
    """
    List contacts in the organization with pagination and filtering.

    Query parameters:
    - **page** - Page number (starts from 1)
    - **page_size** - Number of items per page (max 100)
    - **search** - Search by contact name or email address
    - **owner_id** - Filter by owner (only available for manager/admin/owner roles)

    Members can only see their own contacts. Managers and above can see all contacts.
    """
    service = ContactService(db)

    # Members only see their own contacts
    if org_context.is_member():
        owner_id = org_context.user_id
    elif owner_id is None:
        # If no owner_id specified and not member, show all
        owner_id = None

    contacts = await service.list_contacts(
        org_context.organization_id,
        owner_id=owner_id,
        search=search,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return [ContactResponse.model_validate(c) for c in contacts]


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new contact",
    description=(
        "Create a new contact in the organization. "
        "The current user is automatically set as the owner."
    ),
)
async def create_contact(
    data: ContactCreate,
    org_context: OrgContextDep,
    db: DBSession,
) -> ContactResponse:
    service = ContactService(db)
    contact = await service.create_contact(data, org_context.organization_id, org_context.user_id)
    return ContactResponse.model_validate(contact)


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    summary="Get contact by ID",
    description=(
        "Retrieve detailed information about a specific contact. "
        "Members can only view their own contacts."
    ),
)
async def get_contact(
    *,
    contact_id: int = Path(..., gt=0, description="Contact ID"),
    org_context: OrgContextDep,
    db: DBSession,
) -> ContactResponse:
    service = ContactService(db)
    contact = await service.get_contact(contact_id, org_context.organization_id)

    # Members can only view their own contacts
    check_resource_ownership(org_context, contact.owner_id)

    return ContactResponse.model_validate(contact)


@router.patch(
    "/{contact_id}",
    response_model=ContactResponse,
    summary="Update contact",
    description="Partially update contact information. Members can only update their own contacts.",
)
async def update_contact(
    *,
    contact_id: int = Path(..., gt=0, description="Contact ID"),
    data: ContactUpdate,
    org_context: OrgContextDep,
    db: DBSession,
) -> ContactResponse:
    service = ContactService(db)
    contact = await service.get_contact(contact_id, org_context.organization_id)

    # Members can only update their own contacts
    check_resource_ownership(org_context, contact.owner_id)

    contact = await service.update_contact(contact, data)
    return ContactResponse.model_validate(contact)


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete contact",
    description=(
        "Delete a contact. Cannot delete if the contact has associated deals. "
        "Members can only delete their own contacts."
    ),
)
async def delete_contact(
    *,
    contact_id: int = Path(..., gt=0, description="Contact ID"),
    org_context: OrgContextDep,
    db: DBSession,
) -> None:
    service = ContactService(db)
    contact = await service.get_contact(contact_id, org_context.organization_id)

    # Members can only delete their own contacts
    check_resource_ownership(org_context, contact.owner_id)

    await service.delete_contact(contact)
