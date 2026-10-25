from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        index=True,
    )

    resume_version_id: Mapped[int] = mapped_column(
        ForeignKey("resume_versions.id"),
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="preparing",
    )

    application_url: Mapped[str] = mapped_column(
        String(1000),
        default="",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )