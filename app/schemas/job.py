from pydantic import BaseModel


class JobResponse(BaseModel):
    job_id: int
    job_title: str | None
    company_name: str | None
    employment_type: str | None
    work_type: str | None
    job_location: str | None
    minimum_experience: str | None
    maximum_experience: str | None
    job_status: bool

    class Config:
        from_attributes = True

