from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VulnerabilityEntry(Base):
    __tablename__ = "vulnerability_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    swc_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    code_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    files: Mapped[list["ProjectFile"]] = relationship(back_populates="project")
    analyses: Mapped[list["AnalysisResult"]] = relationship(back_populates="project")
    fuzz_results: Mapped[list["FuzzingResult"]] = relationship(back_populates="project")
    llm_audit_results: Mapped[list["LLMAuditResult"]] = relationship(back_populates="project")
    reports: Mapped[list["Report"]] = relationship(back_populates="project")


class ProjectFile(Base):
    __tablename__ = "project_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    project: Mapped["Project"] = relationship(back_populates="files")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False
    )
    analyzer: Mapped[str] = mapped_column(String(50), server_default="slither")
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="analyses")
    detections: Mapped[list["Detection"]] = relationship(
        back_populates="analysis_result"
    )


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_result_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_results.id"), nullable=False
    )
    detection_ref: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    check_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(50), nullable=True)
    element_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    analysis_result: Mapped["AnalysisResult"] = relationship(
        back_populates="detections"
    )


class FuzzingResult(Base):
    __tablename__ = "fuzzing_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False
    )
    raw_output: Mapped[str] = mapped_column(Text, nullable=False)
    failures_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="fuzz_results")


class LLMAuditResult(Base):
    __tablename__ = "llm_audit_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False
    )
    contract_name: Mapped[str] = mapped_column(String(200), nullable=False)
    function_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    vulnerability_description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    gas_optimization: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="llm_audit_results")


class FalsePositiveFeedback(Base):
    __tablename__ = "false_positive_feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    detection_ref: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    file_paths: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="reports")
