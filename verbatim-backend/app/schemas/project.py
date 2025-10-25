from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: str
    user_id: str
    status: str = "active"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TranscriptionBase(BaseModel):
    project_id: str
    language: str = "en-US"


class TranscriptionCreate(TranscriptionBase):
    file_name: str
    file_size: int


class TranscriptionResponse(TranscriptionBase):
    id: str
    file_url: Optional[str] = None
    transcript_text: Optional[str] = None
    srt_content: Optional[str] = None
    duration: Optional[float] = None
    status: str = "pending"
    created_at: datetime

    class Config:
        from_attributes = True
