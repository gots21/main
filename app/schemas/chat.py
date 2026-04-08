from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    pass  # no body required; person_id comes from URL


class SessionResponse(BaseModel):
    id: int
    person_id: int
    started_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    timestamp: datetime

    model_config = {"from_attributes": True}
