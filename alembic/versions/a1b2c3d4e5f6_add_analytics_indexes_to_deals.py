"""add_analytics_indexes_to_deals

Revision ID: a1b2c3d4e5f6
Revises: 15b77311e587
Create Date: 2025-12-01 23:50:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "15b77311e587"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - add composite indexes for analytics queries."""
    # Composite index for status-based analytics (summary endpoint)
    # Covers: WHERE organization_id = X GROUP BY status
    op.create_index(
        "idx_deals_org_status",
        "deals",
        ["organization_id", "status"],
    )

    # Composite index for time-based analytics (new deals count)
    # Covers: WHERE organization_id = X AND created_at >= date
    op.create_index(
        "idx_deals_org_created",
        "deals",
        ["organization_id", "created_at"],
    )

    # Composite index for funnel analytics
    # Covers: WHERE organization_id = X GROUP BY stage, status
    op.create_index(
        "idx_deals_org_stage_status",
        "deals",
        ["organization_id", "stage", "status"],
    )


def downgrade() -> None:
    """Downgrade schema - remove composite indexes."""
    op.drop_index("idx_deals_org_stage_status", table_name="deals")
    op.drop_index("idx_deals_org_created", table_name="deals")
    op.drop_index("idx_deals_org_status", table_name="deals")
