from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.person import Person
from app.models.session import ChatMessage, ChatSession
from app.schemas.chat import MessageCreate, MessageResponse, SessionResponse
from app.services.claude_client import stream_chat
from app.services.prompt_builder import build_system_prompt
from app.services.vector_store import retrieve_examples

router = APIRouter(tags=["chat"])

DB = Annotated[AsyncSession, Depends(get_db)]


async def _get_person_or_404(person_id: int, db: AsyncSession) -> Person:
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person


async def _get_session_or_404(session_id: int, db: AsyncSession) -> ChatSession:
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return sess


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@router.post(
    "/api/v1/persons/{person_id}/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["chat"],
)
async def create_session(person_id: int, db: DB) -> ChatSession:
    person = await _get_person_or_404(person_id, db)
    prompt = person.system_prompt_cache or build_system_prompt(person)

    sess = ChatSession(person_id=person_id, system_prompt_snapshot=prompt)
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    return sess


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

@router.post("/api/v1/sessions/{session_id}/messages")
async def send_message(session_id: int, body: MessageCreate, db: DB) -> StreamingResponse:
    sess = await _get_session_or_404(session_id, db)

    # Load history
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp)
    )
    messages = result.scalars().all()
    history = [{"role": m.role, "content": m.content} for m in messages]

    # Retrieve relevant few-shot examples from vector store
    dynamic_examples = retrieve_examples(
        person_id=sess.person_id,
        query=body.content,
        k=5,
    )

    # Build prompt — if we have dynamic examples, rebuild the prompt with them
    if dynamic_examples and sess.system_prompt_snapshot:
        # Inject dynamic examples by rebuilding Section 5
        from app.models.person import Person as PersonModel
        person_result = await db.execute(
            select(PersonModel).where(PersonModel.id == sess.person_id)
        )
        person = person_result.scalar_one_or_none()
        if person:
            system_prompt = build_system_prompt(person, few_shot_examples=dynamic_examples)
        else:
            system_prompt = sess.system_prompt_snapshot or ""
    else:
        system_prompt = sess.system_prompt_snapshot or ""

    # Save user message
    user_msg = ChatMessage(session_id=session_id, role="user", content=body.content)
    db.add(user_msg)
    await db.commit()

    # Stream response
    full_response_parts: list[str] = []

    async def generate():
        async for chunk in stream_chat(system_prompt, history, body.content):
            full_response_parts.append(chunk)
            yield f"data: {chunk}\n\n"

        # Save assistant message after streaming completes
        assistant_content = "".join(full_response_parts)
        async with db.begin():
            asst_msg = ChatMessage(
                session_id=session_id, role="assistant", content=assistant_content
            )
            db.add(asst_msg)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get(
    "/api/v1/sessions/{session_id}/messages",
    response_model=list[MessageResponse],
    tags=["chat"],
)
async def get_messages(session_id: int, db: DB) -> list[ChatMessage]:
    await _get_session_or_404(session_id, db)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp)
    )
    return list(result.scalars().all())
