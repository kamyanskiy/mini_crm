"""Activity routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from api.dependencies.organization import OrgContextDep
from api.dependencies.pagination import PaginationParams
from core.database import DBSession
from schemas.activity import ActivityCreate, ActivityResponse
from services.activity_service import ActivityService

PaginationDep = Annotated[PaginationParams, Depends()]

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get(
    "/deals/{deal_id}/activities",
    response_model=list[ActivityResponse],
    summary="List activities for a deal",
    description=(
        "Retrieve a chronological timeline of all activities (comments, "
        "system events, status changes) associated with a specific deal with pagination."
    ),
)
async def list_activities_for_deal(
    *,
    deal_id: int = Path(..., gt=0, description="Deal ID"),
    org_context: OrgContextDep,
    db: DBSession,
    pagination: PaginationDep,
) -> list[ActivityResponse]:
    service = ActivityService(db)
    activities = await service.list_activities_for_deal(
        deal_id, org_context, skip=pagination.skip, limit=pagination.limit
    )
    return [ActivityResponse.model_validate(a) for a in activities]


@router.post(
    "/deals/{deal_id}/activities",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new activity",
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
