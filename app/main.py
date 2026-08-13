from fastapi import FastAPI, Depends

from app.core.auth import verify_api_key,require_admin_scope
from app.api.sync_routes import router as sync_router
from app.api.resume_routes import router as resume_router
from app.api.job_routes import router as job_router
from app.api.job_read_routes import router as job_read_router
from app.api.candidate_routes import router as candidate_router
from app.api.score_routes import router as score_router
from app.api.embedding_routes import router as embedding_router
from app.config import settings
from app.config.logging import logger
from app.workers.scheduler import start_scheduler, shutdown_scheduler
from app.api.score_admin_routes import router as score_admin_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

# Every route below requires a valid X-API-Key header

protected_read = [Depends(verify_api_key)]
protected_admin = [Depends(require_admin_scope)]

# Read-only: any valid key
app.include_router(candidate_router, dependencies=protected_read)
app.include_router(job_read_router, dependencies=protected_read)
app.include_router(score_router, dependencies=protected_read)


# Admin-only: sync, resume/job processing, embedding backfill
app.include_router(sync_router, dependencies=protected_admin)
app.include_router(resume_router, dependencies=protected_admin)
app.include_router(job_router, dependencies=protected_admin)
app.include_router(embedding_router, dependencies=protected_admin)
app.include_router(score_admin_router, dependencies=protected_admin)

@app.on_event("startup")
async def on_startup():
    logger.info(f"{settings.APP_NAME} started in {settings.APP_ENV} mode")
    start_scheduler()


@app.on_event("shutdown")
async def on_shutdown():
    shutdown_scheduler()


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}