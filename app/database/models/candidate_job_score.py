from sqlalchemy import Integer, Float, Text, DateTime, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CandidateJobScore(Base):
    __tablename__ = "candidate_job_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    candidate_id: Mapped[int] = mapped_column(Integer, index=True)
    job_id: Mapped[int] = mapped_column(Integer, index=True)

    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rule_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    semantic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    skills_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    education_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    override_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    override_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    overridden_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        
    matched_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_skills: Mapped[str | None] = mapped_column(Text, nullable=True)

    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    weaknesses: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    llm_reviewed: Mapped[bool] = mapped_column(Boolean ,default= False)
    
    generated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)