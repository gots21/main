from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.person import Person
from app.schemas.person import (
    ChatLogIngest,
    PersonCreate,
    PersonUpdate,
    PersonResponse,
    PersonalitySurvey,
    SystemPromptResponse,
)
from app.services.chat_log_analyzer import analyze_chat_log
from app.services.prompt_builder import build_system_prompt
from app.services.vector_store import upsert_examples, delete_collection

router = APIRouter(prefix="/api/v1/persons", tags=["persons"])

DB = Annotated[AsyncSession, Depends(get_db)]


async def _get_person_or_404(person_id: int, db: AsyncSession) -> Person:
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person


@router.post("", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
async def create_person(body: PersonCreate, db: DB) -> Person:
    person = Person(
        name=body.name,
        birth_year=body.birth_year,
        residence=body.residence,
        career_history=[e.model_dump() for e in body.career_history],
        education=[e.model_dump() for e in body.education],
        interests=body.interests,
        custom_directions=body.custom_directions,
        speech_patterns={},
        feedback_deltas=[],
        mbti_raw={},
    )
    db.add(person)
    await db.commit()
    await db.refresh(person)
    return person


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(person_id: int, db: DB) -> Person:
    return await _get_person_or_404(person_id, db)


@router.patch("/{person_id}", response_model=PersonResponse)
async def update_person(person_id: int, body: PersonUpdate, db: DB) -> Person:
    person = await _get_person_or_404(person_id, db)

    if body.name is not None:
        person.name = body.name
    if body.birth_year is not None:
        person.birth_year = body.birth_year
    if body.residence is not None:
        person.residence = body.residence
    if body.career_history is not None:
        person.career_history = [e.model_dump() for e in body.career_history]
    if body.education is not None:
        person.education = [e.model_dump() for e in body.education]
    if body.interests is not None:
        person.interests = body.interests
    if body.custom_directions is not None:
        person.custom_directions = body.custom_directions

    # Regenerate system prompt cache
    person.system_prompt_cache = build_system_prompt(person)

    await db.commit()
    await db.refresh(person)
    return person


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(person_id: int, db: DB) -> None:
    person = await _get_person_or_404(person_id, db)
    delete_collection(person_id)
    await db.delete(person)
    await db.commit()


@router.post("/{person_id}/survey", response_model=PersonResponse)
async def submit_survey(person_id: int, body: PersonalitySurvey, db: DB) -> Person:
    person = await _get_person_or_404(person_id, db)

    # Derive MBTI type from dimension scores
    dims = body.responses
    mbti = ""
    for pair, key in [("EI", "energy"), ("SN", "information"), ("TF", "decisions"), ("JP", "lifestyle")]:
        dim = dims.get(key)
        if dim:
            # score 1=first letter, 7=second letter
            mbti += pair[0] if dim.score <= 4 else pair[1]

    person.mbti_type = mbti if len(mbti) == 4 else None
    person.mbti_raw = {
        "responses": {k: v.model_dump() for k, v in dims.items()},
        "open_answers": body.open_answers,
    }

    person.system_prompt_cache = build_system_prompt(person)

    await db.commit()
    await db.refresh(person)
    return person


@router.post("/{person_id}/ingest-logs", response_model=PersonResponse)
async def ingest_chat_logs(person_id: int, body: ChatLogIngest, db: DB) -> Person:
    person = await _get_person_or_404(person_id, db)

    patterns = analyze_chat_log(
        raw_text=body.raw_text,
        target_name=body.target_name,
        format_hint=body.format_hint,
        existing_patterns=person.speech_patterns or {},
    )
    person.speech_patterns = patterns

    # Update vector store with new few-shot examples
    examples = patterns.get("few_shot_examples", [])
    upsert_examples(person_id, examples)

    person.system_prompt_cache = build_system_prompt(person)

    await db.commit()
    await db.refresh(person)
    return person


@router.get("/{person_id}/system-prompt", response_model=SystemPromptResponse)
async def get_system_prompt(person_id: int, db: DB) -> dict:
    person = await _get_person_or_404(person_id, db)
    prompt = person.system_prompt_cache or build_system_prompt(person)
    return {"person_id": person_id, "system_prompt": prompt}
