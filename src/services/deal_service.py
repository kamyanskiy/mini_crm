"""Deal service with business logic."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleViolation, PermissionDenied, ResourceNotFound
from models.activity import ActivityType
from models.deal import STAGE_ORDER, Deal, DealStage, DealStatus
from models.types import AuthContext
from repositories.activity_repository import ActivityRepository
from repositories.contact_repository import ContactRepository
from repositories.deal_repository import DealRepository
from schemas.analytics import (
    DealsFunnelResponse,
    DealsSummaryResponse,
    FunnelStageStats,
    StatusSummary,
)
from schemas.deal import DealCreate, DealUpdate


class DealService:
    """Service for deal business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = DealRepository(db)
        self.contact_repo = ContactRepository(db)
        self.activity_repo = ActivityRepository(db)

    async def create_deal(self, data: DealCreate, organization_id: int, owner_id: int) -> Deal:
        """
        Create a new deal.

        Business Rule: Contact must belong to the same organization.
        """
        # Validate contact belongs to same organization if provided
        if data.contact_id:
            contact = await self.contact_repo.get_by_id_in_org(data.contact_id, organization_id)
            if not contact:
                raise BusinessRuleViolation("Contact does not belong to this organization")

        return await self.repo.create(
            title=data.title,
            contact_id=data.contact_id,
            amount=data.amount,
            currency=data.currency,
            status=data.status,
            stage=data.stage,
            organization_id=organization_id,
            owner_id=owner_id,
        )

    async def get_deal(self, deal_id: int, organization_id: int) -> Deal:
        """Get deal by ID."""
        deal = await self.repo.get_by_id_in_org(deal_id, organization_id)
        if not deal:
            raise ResourceNotFound("Deal not found")
        return deal

    async def get_deal_with_activities(self, deal_id: int, organization_id: int) -> Deal:
        """Get deal with activities."""
        deal = await self.repo.get_with_activities(deal_id)
        if not deal or deal.organization_id != organization_id:
            raise ResourceNotFound("Deal not found")
        return deal

    async def update_deal(self, deal: Deal, data: DealUpdate, auth_context: AuthContext) -> Deal:
        """
        Update deal.

        Business Rules:
        - Cannot set status to 'won' if amount <= 0
        - Cannot rollback stage unless admin/owner
        - Auto-creates activity for status/stage changes
        """
        update_data = data.model_dump(exclude_unset=True)

        # Check if updating status to won
        if "status" in update_data and update_data["status"] == DealStatus.WON:
            # Use new amount if provided, otherwise use current
            amount = update_data.get("amount", deal.amount)
            if amount <= Decimal("0"):
                raise BusinessRuleViolation("Cannot close deal as won with amount <= 0")

            # Auto-create activity for status change
            old_status = deal.status
            await self.activity_repo.create(
                deal_id=deal.id,
                author_id=auth_context.user_id,
                type=ActivityType.STATUS_CHANGED,
                payload={"old_status": old_status.value, "new_status": "won"},
            )

        # Check if updating stage
        if "stage" in update_data:
            new_stage = update_data["stage"]
            old_stage = deal.stage

            # Check if moving backwards
            old_order = STAGE_ORDER[old_stage]
            new_order = STAGE_ORDER[new_stage]

            if new_order < old_order:
                # Moving backwards - only admin/owner allowed
                if not auth_context.is_owner_or_admin():
                    raise PermissionDenied("Only admins and owners can rollback deal stages")

            # Auto-create activity for stage change
            await self.activity_repo.create(
                deal_id=deal.id,
                author_id=auth_context.user_id,
                type=ActivityType.STAGE_CHANGED,
                payload={
                    "old_stage": old_stage.value,
                    "new_stage": new_stage.value,
                },
            )

        return await self.repo.update(deal, **update_data)

    async def list_deals(
        self,
        organization_id: int,
        owner_id: int | None = None,
        status: list[DealStatus] | None = None,
        stage: DealStage | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        order_by: str = "created_at",
        order: str = "desc",
        skip: int = 0,
        limit: int = 100,
    ) -> list[Deal]:
        """List deals with filters and sorting."""
        deals: list[Deal] = await self.repo.list_with_filters(
            organization_id=organization_id,
            owner_id=owner_id,
            status=status,
            stage=stage,
            min_amount=min_amount,
            max_amount=max_amount,
            order_by=order_by,
            order=order,
            skip=skip,
            limit=limit,
        )
        return deals

    async def get_deals_summary(self, organization_id: int, days: int = 30) -> DealsSummaryResponse:
        """
        Get analytics summary for deals:
        - Count and sum by status
        - Average amount for won deals
        - New deals in last N days

        Optimized: Uses composite indexes and minimal queries.
        """
        cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

        # Single optimized query using conditional aggregation
        # Uses index: idx_deals_org_status and idx_deals_org_created
        summary_query = (
            select(
                Deal.status,
                func.count(Deal.id).label("count"),
                func.coalesce(func.sum(Deal.amount), Decimal("0")).label("total_amount"),
                func.avg(case((Deal.status == DealStatus.WON, Deal.amount), else_=None)).label(
                    "avg_won_amount"
                ),
                func.sum(case((Deal.created_at >= cutoff_date, 1), else_=0)).label(
                    "new_deals_count"
                ),
            )
            .where(Deal.organization_id == organization_id)
            .group_by(Deal.status)
        )

        result = await self.db.execute(summary_query)
        status_data = result.all()

        by_status = []
        avg_won_amount = None
        new_deals_count = 0

        for row in status_data:
            by_status.append(
                StatusSummary(
                    status=row.status,
                    count=row.count,
                    total_amount=row.total_amount,
                )
            )
            # Extract avg_won_amount from won status row
            if row.status == DealStatus.WON and row.avg_won_amount:
                avg_won_amount = row.avg_won_amount
            # Aggregate new deals count from all statuses
            if row.new_deals_count:
                new_deals_count += row.new_deals_count

        return DealsSummaryResponse(
            by_status=by_status,
            avg_won_amount=avg_won_amount,
            new_deals_last_n_days=new_deals_count,
            days=days,
        )

    async def get_deals_funnel(self, organization_id: int) -> DealsFunnelResponse:
        """
        Get sales funnel analytics:
        - Count by stage and status
        - Conversion rates between stages
        """
        # Get count by stage and status
        funnel_query = (
            select(
                Deal.stage,
                Deal.status,
                func.count(Deal.id).label("count"),
            )
            .where(Deal.organization_id == organization_id)
            .group_by(Deal.stage, Deal.status)
        )

        result = await self.db.execute(funnel_query)
        funnel_data = result.all()

        # Organize data by stage
        stage_stats: dict[DealStage, dict[str, int]] = {}
        stage_totals: dict[DealStage, int] = {}

        for row in funnel_data:
            if row.stage not in stage_stats:
                stage_stats[row.stage] = {}
                stage_totals[row.stage] = 0

            count_value: int = row.count  # type: ignore[assignment]
            stage_stats[row.stage][row.status.value] = count_value
            stage_totals[row.stage] += count_value

        # Build response with conversion rates
        stages: list[FunnelStageStats] = []
        previous_total = None

        for stage in DealStage:
            stage_order = STAGE_ORDER[stage]
            total_count = stage_totals.get(stage, 0)
            status_breakdown = stage_stats.get(stage, {})

            # Calculate conversion from previous stage
            conversion = None
            if previous_total is not None and previous_total > 0:
                conversion = round((total_count / previous_total) * 100, 2)

            stages.append(
                FunnelStageStats(
                    stage=stage,
                    stage_order=stage_order,
                    total_count=total_count,
                    status_breakdown=status_breakdown,
                    conversion_from_previous=conversion,
                )
            )

            previous_total = total_count

        return DealsFunnelResponse(stages=stages)
