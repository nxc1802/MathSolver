from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
import uuid

from app.url_utils import sanitize_url

# --- Auth Schemas ---
class UserProfile(BaseModel):
    id: uuid.UUID
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

class User(BaseModel):
    id: uuid.UUID
    email: EmailStr

# --- Session Schemas ---
class SessionBase(BaseModel):
    title: str = "Bài toán mới"

class SessionCreate(SessionBase):
    pass

class Session(SessionBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Message Schemas ---
class MessageBase(BaseModel):
    role: str
    type: str = "text"
    content: str
    metadata: Dict[str, Any] = {}

class MessageCreate(MessageBase):
    session_id: uuid.UUID

class Message(MessageBase):
    id: uuid.UUID
    session_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

# --- Solve Job Schemas ---
class SolveRequest(BaseModel):
    text: str
    image_url: Optional[str] = None

    @field_validator("image_url", mode="before")
    @classmethod
    def _clean_image_url(cls, v):
        return sanitize_url(v) if v is not None else None

class SolveResponse(BaseModel):
    job_id: str
    status: str

class RenderVideoRequest(BaseModel):
    job_id: Optional[str] = None

class RenderVideoResponse(BaseModel):
    job_id: str
    status: str


class OcrPreviewResponse(BaseModel):
    """Stateless OCR preview before POST .../solve (no DB writes, no job)."""

    ocr_text: str
    user_message: str = ""
    combined_draft: str
