from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    conversation_id: int | None = None
    retention: Literal["save", "ephemeral"] = "save"
    project_id: int | None = None
    web_search: bool = False


class ChatResponse(BaseModel):
    answer: str
    model: str
    conversation_id: int | None
    saved: bool


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    model: str | None
    memory_candidate: bool
    created_at: datetime


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    content_type: str
    retention_type: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut]
    
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class JobProfileUpdate(BaseModel):
    resume_text: str = ""
    target_roles: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)

    remote_ok: bool = True
    posted_within_days: int = 14
    min_match_score: float = 60


class JobProfileOut(JobProfileUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    linkedin_url: str = ""
    created_at: datetime
    updated_at: datetime


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str | None
    location: str | None

    application_url: str | None
    link_status: str

    source: str
    source_url: str
    posted_date_text: str | None
    snippet: str | None

    match_score: float
    freshness_score: float
    location_score: float
    final_score: float

    status: str

    created_at: datetime
    updated_at: datetime

    


class ApplicationLinkUpdate(BaseModel):
    application_url: str


class JobStatusUpdate(BaseModel):
    status: Literal[
        "new",
        "saved",
        "applied",
        "interview",
        "rejected",
        "offer",
        "ignored",
    ]

from typing import Literal


class CareerRecordCreate(BaseModel):

    category: Literal[
        "education",
        "work",
        "project",
        "skill",
        "certification",
    ]

    title: str = Field(
        min_length=1,
        max_length=300,
    )

    organization: str | None = None

    start_date: str | None = None
    end_date: str | None = None

    description: str = ""

    skills: list[str] = Field(
        default_factory=list
    )


class CareerRecordOut(CareerRecordCreate):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    profile_id: int

    created_at: datetime
    updated_at: datetime