from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


MatchStatus = Literal[
    "satisfied",
    "partial",
    "missing",
    "unknown",
]


class RequirementAssessment(BaseModel):
    requirement_type: Literal[
        "required",
        "preferred",
    ]

    category: str

    requirement_text: str

    status: MatchStatus

    evidence: list[str] = Field(
        default_factory=list,
    )

    explanation: str = ""


class CareerMatchExtraction(BaseModel):
    summary: str

    assessments: list[
        RequirementAssessment
    ] = Field(default_factory=list)


class JobMatchOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    job_id: int

    job_requirement_hash: str
    career_profile_hash: str

    match_score: float
    required_score: float
    preferred_score: float

    summary: str

    assessments: list[
        RequirementAssessment
    ]

    strengths: list[str]
    gaps: list[str]
    unknowns: list[str]

    created_at: datetime

    cached: bool = False