"""010 add project scope to false positive feedback

Revision ID: 010
Revises: 009
"""
from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade():
    # Add project_id column (nullable first for existing data)
    op.add_column(
        "false_positive_feedbacks",
        sa.Column("project_id", sa.Integer(), nullable=True),
    )

    # Backfill project_id from detection_ref → detections → analysis_results → project_id
    op.execute("""
        UPDATE false_positive_feedbacks fp
        SET project_id = ar.project_id
        FROM detections d
        JOIN analysis_results ar ON d.analysis_result_id = ar.id
        WHERE fp.detection_ref = d.detection_ref
    """)

    # For any FP records that couldn't be backfilled (orphaned), set to 0
    op.execute("UPDATE false_positive_feedbacks SET project_id = 0 WHERE project_id IS NULL")

    # Now make it non-nullable
    op.alter_column(
        "false_positive_feedbacks",
        "project_id",
        nullable=False,
    )

    # Add index for project-scoped queries
    op.create_index(
        "ix_false_positive_feedbacks_project_id",
        "false_positive_feedbacks",
        ["project_id"],
    )


def downgrade():
    op.drop_index("ix_false_positive_feedbacks_project_id", table_name="false_positive_feedbacks")
    op.drop_column("false_positive_feedbacks", "project_id")
