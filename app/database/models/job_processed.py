from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from pgvector.sqlalchemy import Vector

from app.config import settings

class JobProcessed(Base):
    __tablename__ = "job_processed"

    job_id: Mapped[int] = mapped_column(primary_key=True)

    cleaned_jd: Mapped[str | None] = mapped_column(Text)
    structured_json: Mapped[str | None] = mapped_column(Text)
    
    embedding:Mapped[list[float]] = mapped_column(
        Vector(settings.EMBEDDINGS_DIMENSIONS),nullable= True
    )
    
    
    jd_hash: Mapped[str | None] = mapped_column(String(64))

    parse_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    parse_error: Mapped[str | None] = mapped_column(Text)

    processed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )