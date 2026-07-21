"""012 add state machine constraints

Revision ID: 012
Revises: 011
"""
from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade():
    # Add CHECK constraint on projects.status to only allow valid states
    op.create_check_constraint(
        "ck_projects_status_valid",
        "projects",
        "status IN ('uploaded', 'processing', 'ready')",
    )

    # Add version integer column for optimistic locking (default 0)
    op.add_column(
        "projects",
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("projects", "version")
    op.drop_constraint("ck_projects_status_valid", "projects", type_="check")
