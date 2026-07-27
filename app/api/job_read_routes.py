from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import JobRaw
from app.database.session import get_postgres_session
from app.schemas.job import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_postgres_session),
):
    job = await db.get(JobRaw, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job