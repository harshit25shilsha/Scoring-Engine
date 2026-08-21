from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from app.core.auth import require_scope
from app.api.sync_routes import router as sync_router
from app.api.resume_routes import router as resume_router
from app.api.job_routes import router as job_router
from app.api.job_read_routes import router as job_read_router
from app.api.candidate_routes import router as candidate_router
from app.api.score_routes import router as score_router
from app.api.embedding_routes import router as embedding_router
from app.api.api_key_admin_routes import router as api_key_admin_router
from app.config import settings
from app.config.logging import logger
from app.workers.scheduler import start_scheduler, shutdown_scheduler
from app.api.score_admin_routes import router as score_admin_router

@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info(f"{settings.APP_NAME} started in {settings.APP_ENV} mode")
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Key management is only for key_admin.
protected_admin = [Depends(require_scope("key_admin"))]

# Frontend/read-only APIs: read or read_write.
protected_read = [Depends(require_scope("read", "read_write"))]

# Backend/system APIs: read_write only.
protected_backend = [Depends(require_scope("read_write"))]

app.include_router(api_key_admin_router, dependencies=protected_admin)

app.include_router(candidate_router, dependencies=protected_read)
app.include_router(job_read_router, dependencies=protected_read)
app.include_router(score_router, dependencies=protected_read)

app.include_router(sync_router, dependencies=protected_backend)
app.include_router(resume_router, dependencies=protected_backend)
app.include_router(job_router, dependencies=protected_backend)
app.include_router(embedding_router, dependencies=protected_backend)
app.include_router(score_admin_router, dependencies=protected_backend)

@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}