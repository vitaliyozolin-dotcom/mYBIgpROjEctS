"""APScheduler — cron-задачи для финансового дашборда."""

from __future__ import annotations

import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.models.payment import Payment, PaymentStatus
from app.services.bank_sync import sync_all_accounts

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def job_sync_banks() -> None:
    logger.info("scheduler: starting bank sync")
    result = await sync_all_accounts()
    logger.info("scheduler: bank sync done: %s", result)


async def job_mark_overdue() -> None:
    today = date.today()
    async with async_session_maker() as session:
        stmt = (
            select(Payment)
            .where(Payment.status == PaymentStatus.PENDING)
            .where(Payment.due_date.is_not(None))
            .where(Payment.due_date < today)
        )
        result = await session.execute(stmt)
        payments = result.scalars().all()
        for p in payments:
            p.status = PaymentStatus.OVERDUE
        if payments:
            await session.commit()
    logger.info("scheduler: marked %s payments as overdue", len(payments))


async def job_daily_report() -> None:
    """Сформировать сводку дня (в будущем отправлять в Telegram)."""

    logger.info("scheduler: daily report job (placeholder)")


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        job_sync_banks,
        trigger=IntervalTrigger(minutes=settings.BANK_SYNC_INTERVAL_MINUTES),
        id="bank_sync",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        job_mark_overdue,
        trigger=CronTrigger(hour=1, minute=0),
        id="mark_overdue",
        replace_existing=True,
    )
    scheduler.add_job(
        job_daily_report,
        trigger=CronTrigger(hour=settings.DAILY_REPORT_HOUR, minute=0),
        id="daily_report",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("APScheduler started with %s jobs", len(scheduler.get_jobs()))


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
