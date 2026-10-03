from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, JSON, Float, Integer
from app.database import Base



def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    content_type: Mapped[str] = mapped_column(String(50), default="general")
    retention_type: Mapped[str] = mapped_column(String(30), default="save")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    project: Mapped["Project | None"] = relationship(
        back_populates="conversations",
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memory_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )

class JobProfile(Base):
    __tablename__ = "job_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(
        String(100), default=""
    )

    last_name: Mapped[str] = mapped_column(
        String(100), default=""
    )

    email: Mapped[str] = mapped_column(
        String(200), default=""
    )

    phone: Mapped[str] = mapped_column(
        String(50), default=""
    )

    linkedin_url: Mapped[str] = mapped_column(
        Text, default=""
    )

    resume_file_path: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    resume_text: Mapped[str] = mapped_column(Text, default="")

    target_roles: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
    )

    preferred_locations: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
    )

    remote_ok: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    posted_within_days: Mapped[int] = mapped_column(
        Integer,
        default=14,
    )

    min_match_score: Mapped[float] = mapped_column(
        Float,
        default=60,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(String(300))
    company: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    location: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        default="tavily",
    )

    source_url: Mapped[str] = mapped_column(
        Text,
        unique=True,
    )

    posted_date_text: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    snippet: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    match_score: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    freshness_score: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    location_score: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    final_score: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="new",
    )

    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    application_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    link_status: Mapped[str] = mapped_column(
        String(32),
        default="unverified",
    )

class CareerRecord(Base):
        __tablename__ = "career_records"

        id: Mapped[int] = mapped_column(
            primary_key=True
        )

        profile_id: Mapped[int] = mapped_column(
            ForeignKey("job_profiles.id", ondelete="CASCADE"),
            index=True,
        )

        category: Mapped[str] = mapped_column(
            String(30)
        )

        title: Mapped[str] = mapped_column(
            String(300)
        )

        organization: Mapped[str | None] = mapped_column(
            String(300),
            nullable=True,
        )

        start_date: Mapped[str | None] = mapped_column(
            String(20),
            nullable=True,
        )

        end_date: Mapped[str | None] = mapped_column(
            String(20),
            nullable=True,
        )

        description: Mapped[str] = mapped_column(
            Text,
            default="",
        )

        skills: Mapped[list[str]] = mapped_column(
            JSON,
            default=list,
        )

        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            default=utcnow,
        )

        updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            default=utcnow,
            onupdate=utcnow,
        )