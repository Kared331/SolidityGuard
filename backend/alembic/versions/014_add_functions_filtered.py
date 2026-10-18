"""record keyword-filtered functions

Revision ID: 014
Revises: 013
Create Date: 2026-10-18 00:00:00.000000

P5 measured a 20.9% keyword-filter drop rate on 1763 real DeFi/library
functions. Those units were silently absent from `functions_extracted`.
This column makes the four-term identity assertable:

    functions_extracted == audited + skipped + failed + filtered
"""

from alembic import op
import sqlalchemy as sa


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_runs",
        sa.Column("functions_filtered", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("audit_runs", "functions_filtered")
