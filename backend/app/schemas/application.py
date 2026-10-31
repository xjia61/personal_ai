from pydantic import BaseModel
from datetime import datetime


class PrepareApplicationRequest(BaseModel):
    job_id: int
    resume_version_id: int

class ApplicationOut(BaseModel):
    application_id: int
    job_id: int
    resume_version_id: int
    application_url: str
    status: str
    created_at: datetime

from typing import Literal

ApplicationStatus = Literal[
    "preparing", "ready_for_review", "applied", "screening",
    "interview", "rejected", "offer", "withdrawn",
]


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationSummary(BaseModel):
    id: int
    job_id: int
    job_title: str
    company: str | None
    resume_version_id: int
    resume_name: str
    resume_version: int
    status: str
    application_url: str
    created_at: datetime
