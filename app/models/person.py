from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residence: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Structured background — list of {role, org, years}
    career_history: Mapped[list[Any]] = mapped_column(JSON, default=list)
    # list of {degree, institution, year}
    education: Mapped[list[Any]] = mapped_column(JSON, default=list)
    # list of str
    interests: Mapped[list[Any]] = mapped_column(JSON, default=list)

    # MBTI / personality survey
    mbti_raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    mbti_type: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Extracted from chat logs
    speech_patterns: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Accumulated feedback corrections → injected into prompt as custom rules
    feedback_deltas: Mapped[list[Any]] = mapped_column(JSON, default=list)

    # User-specified personality direction / customisation
    custom_directions: Mapped[list[Any]] = mapped_column(JSON, default=list)

    # Cached system prompt (regenerated when profile changes)
    system_prompt_cache: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
