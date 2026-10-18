"""record unchanged functions for incremental runs

Revision ID: 015
Revises: 014
Create Date: 2026-10-18 00:00:00.000000

Incremental audits only send changed functions to the LLM. The untouched ones
must still be counted, otherwise an incremental run would report "100% coverage"
of a shrunken denominator. Identity becomes five-term:

    functions_extracted == audited + skipped + failed + filtered + unchanged
"""

from alembic import op
import sqlalchemy as sa


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_runs",
        sa.Column("functions_unchanged", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("audit_runs", "functions_unchanged")
