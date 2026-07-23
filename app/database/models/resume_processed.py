from pgvector.sqlalchemy import Vector

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.config import settings

class ResumeProcessed(Base):
    __tablename__ = "resume_processed"

    candidate_id: Mapped[int] = mapped_column(primary_key=True)

    resume_text: Mapped[str | None] = mapped_column(Text)
    cleaned_text: Mapped[str | None] = mapped_column(Text)
    structured_json: Mapped[str | None] = mapped_column(Text)  # populated in next step (Groq)

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.EMBEDDINGS_DIMENSIONS), nullable= True
    )
    
    resume_hash: Mapped[str | None] = mapped_column(String(64))

    parse_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    parse_error: Mapped[str | None] = mapped_column(Text)

    processed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )