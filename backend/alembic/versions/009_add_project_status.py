"""009 add project status

Revision ID: 009
Revises: 008
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "projects",
        sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
    )
    op.execute("UPDATE projects SET status = 'ready'")
    op.create_index("ix_projects_status", "projects", ["status"])


def downgrade():
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_column("projects", "status")
