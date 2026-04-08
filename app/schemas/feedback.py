from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Correction(BaseModel):
    aspect: str = Field(..., description="e.g. 'humor', 'formality', 'vocabulary'")
    current_behavior: str
    desired_behavior: str


class FeedbackCreate(BaseModel):
    realism_score: int = Field(..., ge=1, le=5)
    personality_accuracy: int = Field(..., ge=1, le=5)
    communication_style_accuracy: int = Field(..., ge=1, le=5)
    humor_accuracy: int = Field(..., ge=1, le=5)
    knowledge_accuracy: int = Field(..., ge=1, le=5)
    corrections: list[Correction] = []
    missing_traits: list[str] = []
    extra_traits: list[str] = []
    general_feedback: str | None = None


class FeedbackResponse(BaseModel):
    id: int
    session_id: int
    realism_score: int
    personality_accuracy: int
    communication_style_accuracy: int
    humor_accuracy: int
    knowledge_accuracy: int
    corrections: list[Any]
    missing_traits: list[Any]
    extra_traits: list[Any]
    general_feedback: str | None
    submitted_at: datetime

    model_config = {"from_attributes": True}
