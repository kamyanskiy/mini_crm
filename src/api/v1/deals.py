"""Deal routes."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel

from api.dependencies.organization import OrgContextDep
from api.dependencies.pagination import PaginationParams
from api.dependencies.permissions import check_resource_ownership
from core.config import settings
from core.database import DBSession
from core.redis import CacheDep
from models.deal import DealStage, DealStatus
from schemas.activity import ActivityCreate, ActivityResponse
from schemas.deal import DealCreate, DealResponse, DealUpdate
from services.activity_service import ActivityService
from services.deal_service import DealService

PaginationDep = Annotated[PaginationParams, Depends()]

router = APIRouter(prefix="/deals", tags=["deals"])


class DealStatusesResponse(BaseModel):
    """Response with available deal statuses and stages."""

    statuses: list[str]
    stages: list[str]


@router.get(
    "/statuses",
    response_model=DealStatusesResponse,
    summary="Get available deal statuses and stages",
)
async def get_deal_statuses(cache: CacheDep) -> DealStatusesResponse:
    """
    Get available deal statuses and stages for the CRM.

    Returns:
    - **statuses** - list of available deal statuses (new, in_progress, won, lost)
    - **stages** - list of available pipeline stages
      (lead, qualification, proposal, negotiation, closed)

    Result is cached for 1 hour as this data rarely changes.
    """
    cache_key = "deals:statuses"

    # Try cache first
    cached = await cache.get_json(cache_key)
    if cached:
        return DealStatusesResponse(**cached)

    # Build response
    result = DealStatusesResponse(
        statuses=[status.value for status in DealStatus],
        stages=[stage.value for stage in DealStage],
    )

    # Cache for 1 hour
    await cache.set_json(
        cache_key, result.model_dump(), expire=settings.view_cache_expire_in_seconds
    )

    return result


@router.get(
    "",
    response_model=list[DealResponse],
    summary="List deals",
)
async def list_deals(
    org_context: OrgContextDep,
    db: DBSession,
    pagination: PaginationDep,
    status: list[DealStatus] = Query(default=None, description="Filter by status(es)"),
    stage: DealStage | None = Query(None, description="Filter by stage"),
    min_amount: Decimal | None = Query(None, ge=0, description="Minimum deal amount"),
    max_amount: Decimal | None = Query(None, ge=0, description="Maximum deal amount"),
    owner_id: int | None = Query(None, gt=0, description="Filter by owner ID"),
    order_by: str = Query(
        "created_at",
        pattern="^(created_at|updated_at|amount|title)$",
        description="Sort field",
    ),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
) -> list[DealResponse]:
    """
    List deals in the organization with advanced filtering and pagination.

    Query parameters:
    - **page** - Page number (starts from 1)
    - **page_size** - Number of items per page (max 100)
    - **status** - Filter by status(es), supports multiple values
      (e.g., ?status=new&status=in_progress)
    - **stage** - Filter by pipeline stage
      (lead, qualification, proposal, negotiation, closed)
    - **min_amount** - Minimum deal amount for filtering
    - **max_amount** - Maximum deal amount for filtering
    - **owner_id** - Filter by owner (only available for manager/admin/owner roles)
    - **order_by** - Sort field (created_at, amount, updated_at, etc.)
    - **order** - Sort order (asc or desc)

    Members can only see their own deals. Managers and above can see all deals.
    """
    service = DealService(db)

    # Members only see their own deals
    if org_context.is_member():
        owner_id = org_context.user_id
    elif owner_id is None:
        # If no owner_id specified and not member, show all
        owner_id = None

    deals = await service.list_deals(
        org_context.organization_id,
        owner_id=owner_id,
        status=status,
        stage=stage,
        min_amount=min_amount,
        max_amount=max_amount,
        order_by=order_by,
        order=order,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return [DealResponse.model_validate(d) for d in deals]


@router.post(
    "",
    response_model=DealResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new deal",
    description=(
        "Create a new deal in the organization. "
        "The current user is automatically set as the owner. Invalidates analytics cache."
    ),
)
async def create_deal(
    data: DealCreate,
    org_context: OrgContextDep,
    db: DBSession,
    cache: CacheDep,
) -> DealResponse:
    service = DealService(db)
    deal = await service.create_deal(data, org_context.organization_id, org_context.user_id)

    # Invalidate analytics cache
    await cache.delete_pattern(f"analytics:*:{org_context.organization_id}*")

    return DealResponse.model_validate(deal)


@router.get(
    "/{deal_id}",
    response_model=DealResponse,
    summary="Get deal by ID",
    description=(
        "Retrieve detailed information about a specific deal including its activity timeline. "
        "Members can only view their own deals."
    ),
)
async def get_deal(
    *,
    deal_id: int = Path(..., gt=0, description="Deal ID"),
    org_context: OrgContextDep,
    db: DBSession,
) -> DealResponse:
    service = DealService(db)
    deal = await service.get_deal_with_activities(deal_id, org_context.organization_id)

    # Members can only view their own deals
    check_resource_ownership(org_context, deal.owner_id)

    return DealResponse.model_validate(deal)


@router.patch(
    "/{deal_id}",
    response_model=DealResponse,
    summary="Update deal",
)
async def update_deal(
    *,
    deal_id: int = Path(..., gt=0, description="Deal ID"),
    data: DealUpdate,
    org_context: OrgContextDep,
    db: DBSession,
    cache: CacheDep,
) -> DealResponse:
    """
    Update deal (partial update). Members can only update their own deals.

    Business rules:
    - **Cannot set status to 'won' if amount <= 0** - deals must have positive value to be won
    - **Cannot rollback stage** - only admins/owners can move deals backwards in the pipeline
    - **Auto-creates activity** - system automatically logs status/stage changes to deal timeline

    Invalidates analytics cache after successful update.
    """
    from models.types import AuthContext

    service = DealService(db)
    deal = await service.get_deal(deal_id, org_context.organization_id)

    # Members can only update their own deals
    check_resource_ownership(org_context, deal.owner_id)

    # Convert HTTP context to domain AuthContext
    auth_context = AuthContext(
        user_id=org_context.user_id,
        organization_id=org_context.organization_id,
        role=org_context.role,
    )

    deal = await service.update_deal(deal, data, auth_context)

    # Invalidate analytics cache
    await cache.delete_pattern(f"analytics:*:{org_context.organization_id}*")

    return DealResponse.model_validate(deal)


@router.get(
    "/{deal_id}/activities",
    response_model=list[ActivityResponse],
    summary="List activities for a deal",
    description=(
        "Retrieve a chronological timeline of all activities "
        "(comments, system events, status changes) for a specific deal."
    ),
)
async def list_activities_for_deal(
    *,
    deal_id: int = Path(..., gt=0, description="Deal ID"),
    org_context: OrgContextDep,
    db: DBSession,
) -> list[ActivityResponse]:
    service = ActivityService(db)
    activities = await service.list_activities_for_deal(deal_id, org_context)
    return [ActivityResponse.model_validate(a) for a in activities]


@router.post(
    "/{deal_id}/activities",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create activity for a deal",
    description="Add a new activity (comment, note, or system event) to a deal's timeline.",
)
async def create_activity(
    *,
    deal_id: int = Path(..., gt=0, description="Deal ID"),
    data: ActivityCreate,
    org_context: OrgContextDep,
    db: DBSession,
) -> ActivityResponse:
    service = ActivityService(db)
    activity = await service.create_activity(data, deal_id, org_context)
    return ActivityResponse.model_validate(activity)
