from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FeedbackSurvey(Base):
    __tablename__ = "feedback_surveys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_sessions.id"), nullable=False
    )

    # Likert 1–5 scores
    realism_score: Mapped[int] = mapped_column(Integer, nullable=False)
    personality_accuracy: Mapped[int] = mapped_column(Integer, nullable=False)
    communication_style_accuracy: Mapped[int] = mapped_column(Integer, nullable=False)
    humor_accuracy: Mapped[int] = mapped_column(Integer, nullable=False)
    knowledge_accuracy: Mapped[int] = mapped_column(Integer, nullable=False)

    # Specific corrections: list of {aspect, current_behavior, desired_behavior}
    corrections: Mapped[list[Any]] = mapped_column(JSON, default=list)
    # Traits felt missing
    missing_traits: Mapped[list[Any]] = mapped_column(JSON, default=list)
    # Traits that feel wrong / out of character
    extra_traits: Mapped[list[Any]] = mapped_column(JSON, default=list)

    general_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
