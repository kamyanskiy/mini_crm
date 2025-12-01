from decimal import Decimal

from pydantic import BaseModel

from models.deal import DealStage, DealStatus


class StatusSummary(BaseModel):
    """Summary for a specific status."""

    status: DealStatus
    count: int
    total_amount: Decimal


class DealsSummaryResponse(BaseModel):
    """Analytics summary for deals."""

    by_status: list[StatusSummary]
    avg_won_amount: Decimal | None
    new_deals_last_n_days: int
    days: int = 30


class FunnelStageStats(BaseModel):
    """Statistics for a funnel stage."""

    stage: DealStage
    stage_order: int
    total_count: int
    status_breakdown: dict[str, int]  # status -> count
    conversion_from_previous: float | None  # percentage


class DealsFunnelResponse(BaseModel):
    """Sales funnel analytics."""

    stages: list[FunnelStageStats]
