from fastapi import FastAPI

from app.api.sync_routes import router as sync_router
from app.api.resume_routes import router as resume_router
from app.config import settings
from app.config.logging import logger
from app.workers.scheduler import start_scheduler, shutdown_scheduler
from app.api.job_routes import router as job_router
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.include_router(sync_router)
app.include_router(resume_router)
app.include_router(job_router)


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