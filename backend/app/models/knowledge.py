from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VulnerabilityEntry(Base):
    __tablename__ = "vulnerability_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    swc_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    code_example: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )