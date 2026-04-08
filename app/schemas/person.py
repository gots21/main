from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CareerEntry(BaseModel):
    role: str
    org: str
    years: str = ""  # e.g. "2018-2022"


class EducationEntry(BaseModel):
    degree: str
    institution: str
    year: int | None = None


class PersonCreate(BaseModel):
    name: str
    birth_year: int | None = None
    residence: str | None = None
    career_history: list[CareerEntry] = []
    education: list[EducationEntry] = []
    interests: list[str] = []
    custom_directions: list[str] = []


class PersonUpdate(BaseModel):
    name: str | None = None
    birth_year: int | None = None
    residence: str | None = None
    career_history: list[CareerEntry] | None = None
    education: list[EducationEntry] | None = None
    interests: list[str] | None = None
    custom_directions: list[str] | None = None


class MBTIDimension(BaseModel):
    score: int = Field(..., ge=1, le=7)
    label: str = ""


class PersonalitySurvey(BaseModel):
    responses: dict[str, MBTIDimension] = Field(
        ...,
        description=(
            "Keys: energy (E-I), information (S-N), decisions (T-F), lifestyle (J-P), "
            "assertiveness, emotional_expression, conflict_style, social_energy"
        ),
    )
    open_answers: dict[str, str] = Field(
        default_factory=dict,
        description="Keys: self_description, values, stress_response",
    )


class ChatLogIngest(BaseModel):
    target_name: str = Field(..., description="Name of the target person as it appears in the chat log")
    raw_text: str = Field(..., description="Full raw chat log text")
    format_hint: str = Field(
        default="auto",
        description="Format hint: 'kakao', 'whatsapp', 'imessage', or 'auto'",
    )


class PersonResponse(BaseModel):
    id: int
    name: str
    birth_year: int | None
    residence: str | None
    career_history: list[Any]
    education: list[Any]
    interests: list[Any]
    mbti_type: str | None
    speech_patterns: dict[str, Any]
    feedback_deltas: list[Any]
    custom_directions: list[Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SystemPromptResponse(BaseModel):
    person_id: int
    system_prompt: str
