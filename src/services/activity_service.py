"""Activity service with business logic."""

from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.organization import OrgContext
from core.exceptions import ResourceNotFound
from models.activity import Activity, ActivityType
from repositories.activity_repository import ActivityRepository
from repositories.deal_repository import DealRepository
from schemas.activity import ActivityCreate


class ActivityService:
    """Service for activity business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ActivityRepository(db)
        self.deal_repo = DealRepository(db)

    async def create_activity(
        self, data: ActivityCreate, deal_id: int, org_context: OrgContext
    ) -> Activity:
        """Create a new activity (e.g., comment)."""
        # Verify deal exists and belongs to organization
        deal = await self.deal_repo.get_by_id_in_org(deal_id, org_context.organization_id)
        if not deal:
            raise ResourceNotFound("Deal not found")

        return await self.repo.create(
            deal_id=deal_id,
            author_id=org_context.user_id,
            type=data.type,
            payload=data.payload,
        )

    async def log_system_activity(
        self, deal_id: int, activity_type: ActivityType, payload: dict
    ) -> Activity:
        """Log a system-generated activity."""
        return await self.repo.create(
            deal_id=deal_id, author_id=None, type=activity_type, payload=payload
        )

    async def list_activities_for_deal(
        self, deal_id: int, org_context: OrgContext
    ) -> list[Activity]:
        """List all activities for a deal."""
        # Verify deal exists and belongs to organization
        deal = await self.deal_repo.get_by_id_in_org(deal_id, org_context.organization_id)
        if not deal:
            raise ResourceNotFound("Deal not found")

        activities: list[Activity] = await self.repo.list_by_deal(deal_id)
        return activities
