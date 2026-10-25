from app.legacy_models import (
    Conversation,
    Message,
    Project,
    JobProfile,
    CareerRecord,
    ResumeVersion,
    JobRequirement,
    utcnow,
    Job,
    # 其他旧 models 继续放这里
)

from app.models.job_match import JobMatchAnalysis
from app.models.application import Application
from app.models.application_profile import ApplicationProfile