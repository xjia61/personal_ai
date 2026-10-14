from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobMatchAnalysis(Base):
    __tablename__ = "job_match_analyses"

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "job_requirement_hash",
            "career_profile_hash",
            name="uq_job_match_cache",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
    )

    job_requirement_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )

    career_profile_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )

    match_score: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    required_score: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    preferred_score: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        default="",
    )

    assessments: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    strengths: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    gaps: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    unknowns: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )