from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_tables
from app.routers import persons, chat, feedback


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (idempotent; production uses Alembic)
    await create_tables()
    yield


app = FastAPI(
    title="AI Personality Cloning System",
    description=(
        "Clone a real person's communication style and personality using Claude. "
        "Ingest profile data, chat logs, and personality surveys to build an AI replica. "
        "Refine iteratively via post-conversation feedback surveys."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(persons.router)
app.include_router(chat.router)
app.include_router(feedback.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
