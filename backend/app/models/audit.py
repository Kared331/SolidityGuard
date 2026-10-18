from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:  # 关系类型注解用；运行期由 models/__init__ 注册，避免循环导入
    from app.models.project import Project


class FuzzingResult(Base):
    __tablename__ = "fuzzing_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    raw_output: Mapped[str] = mapped_column(Text, nullable=False)
    failures_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="fuzz_results")


class AuditRun(Base):
    """One LLM audit execution: the ledger that makes coverage assertable.

    Two identities must hold for every row:
        files_total          == files_processed + files_unreadable
        functions_extracted  == audited + skipped + failed + filtered

    `filtered` = dropped by the keyword pre-filter, never sent to the LLM.
    It is recorded instead of disappearing, so the denominator is the real
    function count of the source, not the post-filter count.
    """

    __tablename__ = "audit_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    kb_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    files_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_unreadable: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    functions_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    functions_audited: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    functions_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    functions_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    functions_filtered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rag_hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rag_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="audit_runs")


class LLMAuditResult(Base):
    __tablename__ = "llm_audit_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    audit_run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("audit_runs.id"), nullable=True, index=True)
    contract_name: Mapped[str] = mapped_column(String(200), nullable=False)
    function_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    vulnerability_description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    gas_optimization: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="llm_audit_results")
