from sqlalchemy import Boolean, Integer, String, Text, DateTime

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.database.base import Base
from app.database.models.base_model import TimestampMixin


class CandidateRaw(Base, TimestampMixin):
    __tablename__ = "candidate_raw"

    candidate_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))

    current_designation: Mapped[str | None] = mapped_column(String(255))

    currently_working_company_name: Mapped[str | None] = mapped_column(
        String(255)
    )

    key_experience: Mapped[str | None] = mapped_column(String(100))

    key_experience_in_month: Mapped[int | None] = mapped_column(Integer)

    overview: Mapped[str | None] = mapped_column(Text)

    resume_file_name: Mapped[str | None] = mapped_column(String(500))

    resume_file_url: Mapped[str | None] = mapped_column(Text)

    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))

    active_status: Mapped[bool] = mapped_column(Boolean)

    is_rejected: Mapped[bool] = mapped_column(Boolean)

    candidate_type: Mapped[str | None] = mapped_column(String(50))

    vendor_id: Mapped[int | None] = mapped_column(Integer)

    sync_status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
    )

    resume_processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    last_synced_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    