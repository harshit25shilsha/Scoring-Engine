from pydantic import BaseModel


class CandidateResponse(BaseModel):
    candidate_id: int
    first_name: str | None
    last_name: str | None
    email: str | None
    current_designation: str | None
    currently_working_company_name: str | None
    city: str | None
    state: str | None
    country: str | None
    candidate_type: str | None

    class Config:
        from_attributes = True


class CandidateScoreResponse(BaseModel):
    job_id: int
    overall_score: float | None
    rule_score: float | None
    semantic_score: float | None
    recommendation: str | None

    class Config:
        from_attributes = True
        
