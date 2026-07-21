"""011 add foreign key indexes

Revision ID: 011
Revises: 010
"""
from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade():
    # Add indexes on all foreign key columns for query performance
    op.create_index("ix_analysis_results_project_id", "analysis_results", ["project_id"])
    op.create_index("ix_detections_analysis_result_id", "detections", ["analysis_result_id"])
    op.create_index("ix_fuzzing_results_project_id", "fuzzing_results", ["project_id"])
    op.create_index("ix_llm_audit_results_project_id", "llm_audit_results", ["project_id"])
    op.create_index("ix_project_files_project_id", "project_files", ["project_id"])
    op.create_index("ix_reports_project_id", "reports", ["project_id"])


def downgrade():
    op.drop_index("ix_reports_project_id", table_name="reports")
    op.drop_index("ix_project_files_project_id", table_name="project_files")
    op.drop_index("ix_llm_audit_results_project_id", table_name="llm_audit_results")
    op.drop_index("ix_fuzzing_results_project_id", table_name="fuzzing_results")
    op.drop_index("ix_detections_analysis_result_id", table_name="detections")
    op.drop_index("ix_analysis_results_project_id", table_name="analysis_results")
