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


class LLMAuditResult(Base):
    __tablename__ = "llm_audit_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    contract_name: Mapped[str] = mapped_column(String(200), nullable=False)
    function_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    vulnerability_description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    gas_optimization: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="llm_audit_results")
