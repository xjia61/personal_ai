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