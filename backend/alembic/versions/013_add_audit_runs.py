"""add audit_runs ledger

Revision ID: 013
Revises: 012
Create Date: 2026-10-18 00:00:00.000000

Two identities this table must make assertable:
    files_total         == files_processed + files_unreadable
    functions_extracted == functions_audited + functions_skipped + functions_failed
"""

from alembic import op
import sqlalchemy as sa


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None

_COUNTERS = (
    "files_total",
    "files_processed",
    "files_unreadable",
    "functions_extracted",
    "functions_audited",
    "functions_skipped",
    "functions_failed",
    "invalid_findings",
    "rag_hits",
    "rag_failures",
)


def upgrade() -> None:
    op.create_table(
        "audit_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="running", nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("kb_version", sa.String(length=50), nullable=True),
        *[sa.Column(name, sa.Integer(), server_default="0", nullable=False) for name in _COUNTERS],
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_runs_project_id", "audit_runs", ["project_id"])

    op.add_column("llm_audit_results", sa.Column("audit_run_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_llm_audit_results_audit_run_id",
        "llm_audit_results",
        "audit_runs",
        ["audit_run_id"],
        ["id"],
    )
    op.create_index("ix_llm_audit_results_audit_run_id", "llm_audit_results", ["audit_run_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_audit_results_audit_run_id", table_name="llm_audit_results")
    op.drop_constraint("fk_llm_audit_results_audit_run_id", "llm_audit_results", type_="foreignkey")
    op.drop_column("llm_audit_results", "audit_run_id")
    op.drop_index("ix_audit_runs_project_id", table_name="audit_runs")
    op.drop_table("audit_runs")
