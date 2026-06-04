"""Add detections and false_positive_feedbacks tables

Revision ID: 004
Revises: 003
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "detections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "analysis_result_id",
            sa.Integer(),
            sa.ForeignKey("analysis_results.id"),
            nullable=False,
        ),
        sa.Column("detection_ref", sa.String(length=500), nullable=False),
        sa.Column("check_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("impact", sa.String(length=50), nullable=True),
        sa.Column("confidence", sa.String(length=50), nullable=True),
        sa.Column("element_json", JSON, nullable=True),
    )
    op.create_index(
        "ix_detections_detection_ref",
        "detections",
        ["detection_ref"],
    )

    op.create_table(
        "false_positive_feedbacks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("detection_ref", sa.String(length=500), nullable=False),
        sa.Column("user_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_false_positive_feedbacks_detection_ref",
        "false_positive_feedbacks",
        ["detection_ref"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_false_positive_feedbacks_detection_ref",
        table_name="false_positive_feedbacks",
    )
    op.drop_table("false_positive_feedbacks")
    op.drop_index(
        "ix_detections_detection_ref",
        table_name="detections",
    )
    op.drop_table("detections")
