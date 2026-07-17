from sqlalchemy import Boolean, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.models.base_model import TimestampMixin


class JobRaw(Base, TimestampMixin):
    __tablename__ = "jobs_raw"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    job_title: Mapped[str | None] = mapped_column(String(255))
    company_name: Mapped[str | None] = mapped_column(String(255))
    job_description: Mapped[str | None] = mapped_column(Text)

    minimum_experience: Mapped[str | None] = mapped_column(String(50))
    maximum_experience: Mapped[str | None] = mapped_column(String(50))

    minimum_qualification: Mapped[str | None] = mapped_column(String(255))
    preffered_qualification: Mapped[str | None] = mapped_column(String(255))

    employment_type: Mapped[str | None] = mapped_column(String(100))
    work_type: Mapped[str | None] = mapped_column(String(100))

    job_location: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))

    notice_period: Mapped[str | None] = mapped_column(String(100))

    job_status: Mapped[bool] = mapped_column(Boolean)
    jobs_posted_status: Mapped[str | None] = mapped_column(String(50))

    vendor_id: Mapped[int | None] = mapped_column(Integer)

    sync_status: Mapped[str] = mapped_column(String(20), default="PENDING")

    jd_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    last_synced_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )