from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.state.project_state import ProjectStatus


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=ProjectStatus.UPLOADED.value,
        nullable=False,
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
        Integer, ForeignKey("projects.id"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    project: Mapped["Project"] = relationship(back_populates="files")