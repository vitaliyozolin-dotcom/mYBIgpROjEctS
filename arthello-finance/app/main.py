import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import accounts, companies, dashboard, dds_categories, payments
from app.services.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()
        logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    description="Финансовый дашборд группы компаний ARTHELLO",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(accounts.router)
app.include_router(payments.router)
app.include_router(dds_categories.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}
