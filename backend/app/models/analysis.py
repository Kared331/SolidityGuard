from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from typing import Optional
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False, index=True
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
        Integer, ForeignKey("analysis_results.id"), nullable=False, index=True
    )
    detection_ref: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    check_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    element_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    analysis_result: Mapped["AnalysisResult"] = relationship(
        back_populates="detections"
    )