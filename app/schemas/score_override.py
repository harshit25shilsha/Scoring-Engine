from pydantic import BaseModel, Field


class ScoreOverrideRequest(BaseModel):
    override_score: float = Field(..., ge=0, le=100)
    note: str = Field(..., min_length=1, max_length=1000)