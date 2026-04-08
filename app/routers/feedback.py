from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.feedback import FeedbackSurvey
from app.models.person import Person
from app.models.session import ChatSession
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.services.feedback_processor import apply_feedback_to_person
from app.services.prompt_builder import build_system_prompt

router = APIRouter(tags=["feedback"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/api/v1/sessions/{session_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(session_id: int, body: FeedbackCreate, db: DB) -> FeedbackSurvey:
    # Verify session exists
    sess_result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    sess = sess_result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    survey = FeedbackSurvey(
        session_id=session_id,
        realism_score=body.realism_score,
        personality_accuracy=body.personality_accuracy,
        communication_style_accuracy=body.communication_style_accuracy,
        humor_accuracy=body.humor_accuracy,
        knowledge_accuracy=body.knowledge_accuracy,
        corrections=[c.model_dump() for c in body.corrections],
        missing_traits=body.missing_traits,
        extra_traits=body.extra_traits,
        general_feedback=body.general_feedback,
    )
    db.add(survey)
    await db.flush()  # get survey.id without committing yet

    # Update person profile with feedback deltas
    person_result = await db.execute(select(Person).where(Person.id == sess.person_id))
    person = person_result.scalar_one_or_none()
    if person:
        apply_feedback_to_person(person, survey)
        person.system_prompt_cache = build_system_prompt(person)

    await db.commit()
    await db.refresh(survey)
    return survey


@router.get(
    "/api/v1/persons/{person_id}/feedback-history",
    response_model=list[FeedbackResponse],
)
async def get_feedback_history(person_id: int, db: DB) -> list[FeedbackSurvey]:
    # Verify person exists
    person_result = await db.execute(select(Person).where(Person.id == person_id))
    if not person_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    result = await db.execute(
        select(FeedbackSurvey)
        .join(ChatSession, FeedbackSurvey.session_id == ChatSession.id)
        .where(ChatSession.person_id == person_id)
        .order_by(FeedbackSurvey.submitted_at.desc())
    )
    return list(result.scalars().all())
