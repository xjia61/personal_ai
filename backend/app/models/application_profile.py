from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base   # 用你项目实际 Base import


class ApplicationProfile(Base):
    __tablename__ = "application_profiles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    email: Mapped[str] = mapped_column(
        String(200),
        default="",
    )

    phone: Mapped[str] = mapped_column(
        String(50),
        default="",
    )

    address: Mapped[str] = mapped_column(
        String(300),
        default="",
    )

    city: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    state: Mapped[str] = mapped_column(
        String(100),
        default="",
    )

    zip_code: Mapped[str] = mapped_column(
        String(20),
        default="",
    )

    linkedin_url: Mapped[str] = mapped_column(
        String(500),
        default="",
    )

    github_url: Mapped[str] = mapped_column(
        String(500),
        default="",
    )

    portfolio_url: Mapped[str] = mapped_column(
        String(500),
        default="",
    )

    authorized_to_work: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    requires_sponsorship: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )