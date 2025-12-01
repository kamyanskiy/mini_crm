"""Analytics routes."""

from fastapi import APIRouter, Query

from api.dependencies.organization import OrgContextDep
from core.config import settings
from core.database import DBSession
from core.redis import CacheDep
from schemas.analytics import DealsFunnelResponse, DealsSummaryResponse
from services.deal_service import DealService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/deals/summary",
    response_model=DealsSummaryResponse,
    summary="Get deals summary analytics",
)
async def get_deals_summary(
    org_context: OrgContextDep,
    db: DBSession,
    cache: CacheDep,
    days: int = Query(default=30, ge=1, le=365, description="Number of days for new deals count"),
) -> DealsSummaryResponse:
    """
    Get comprehensive deals summary analytics for the organization.

    Returns aggregated statistics:
    - **Count of deals by status** (new, in_progress, won, lost)
    - **Total amount by status** - sum of all deal amounts per status
    - **Average amount for won deals** - mean value of successfully closed
    - **Number of new deals** created in the last N days (configurable)

    Result is cached for 5 minutes for performance optimization.
    """
    cache_key = f"analytics:summary:{org_context.organization_id}:{days}"

    # Try cache first
    cached = await cache.get_json(cache_key)
    if cached:
        return DealsSummaryResponse(**cached)

    # Get fresh data
    service = DealService(db)
    result = await service.get_deals_summary(org_context.organization_id, days=days)

    # Cache result
    await cache.set_json(
        cache_key,
        result.model_dump(),
        expire=settings.unit_cache_expire_in_seconds,
    )

    return result


@router.get(
    "/deals/funnel",
    response_model=DealsFunnelResponse,
    summary="Get sales funnel analytics",
)
async def get_deals_funnel(
    org_context: OrgContextDep,
    db: DBSession,
    cache: CacheDep,
) -> DealsFunnelResponse:
    """
    Get detailed sales funnel analytics for the organization.

    Returns stage-by-stage breakdown:
    - **Count of deals by stage** (lead, qualification, proposal, negotiation)
    - **Status breakdown** - distribution of deal statuses within each stage
    - **Conversion rate** - percentage of deals progressing from previous stage

    Result is cached for 5 minutes for performance optimization.
    """
    cache_key = f"analytics:funnel:{org_context.organization_id}"

    # Try cache first
    cached = await cache.get_json(cache_key)
    if cached:
        return DealsFunnelResponse(**cached)

    # Get fresh data
    service = DealService(db)
    result = await service.get_deals_funnel(org_context.organization_id)

    # Cache result
    await cache.set_json(
        cache_key,
        result.model_dump(),
        expire=settings.unit_cache_expire_in_seconds,
    )

    return result
