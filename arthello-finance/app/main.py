import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.config import settings
from app.database import async_session_maker, get_db
from app.routers import accounts, companies, dashboard, dds_categories, payments
from app.seeds import seed_all
from app.services.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)
    try:
        async with async_session_maker() as session:
            counts = await seed_all(session)
            await session.commit()
        logger.info("seed on startup: %s", counts)
    except Exception:  # noqa: BLE001
        logger.exception("seed on startup failed, continuing")
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
async def health(db: AsyncSession = Depends(get_db)):
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("health: DB ping failed: %s", exc)
        db_status = "error"
    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "db": db_status,
        "version": __version__,
    }
