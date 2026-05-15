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
from app.models.account import Bank
from app.models.oauth_token import OAuthToken
from app.models.payment import PaymentQueue, PaymentStatus
from app.services.bank_sync import sync_all_accounts
from app.services.tochka import TochkaError, get_balances

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def job_sync_banks() -> None:
    logger.info("scheduler: starting bank sync")
    result = await sync_all_accounts()
    logger.info("scheduler: bank sync done: %s", result)


async def job_mark_overdue() -> None:
    """Помечает просроченные платежи: статус остаётся PENDING, но повышаем priority до 1."""

    today = date.today()
    async with async_session_maker() as session:
        stmt = (
            select(PaymentQueue)
            .where(PaymentQueue.status == PaymentStatus.PENDING)
            .where(PaymentQueue.due_date.is_not(None))
            .where(PaymentQueue.due_date < today)
            .where(PaymentQueue.priority > 1)
        )
        result = await session.execute(stmt)
        payments = result.scalars().all()
        for p in payments:
            p.priority = 1
        if payments:
            await session.commit()
    logger.info("scheduler: escalated %s overdue payments to priority=1", len(payments))


async def job_daily_report() -> None:
    """Сформировать сводку дня (в будущем отправлять в Telegram)."""

    logger.info("scheduler: daily report job (placeholder)")


async def job_tochka_balances() -> None:
    """Каждые N часов вытягиваем остатки из Точки для всех компаний с токеном."""

    async with async_session_maker() as session:
        result = await session.execute(
            select(OAuthToken.company_id).where(OAuthToken.bank == Bank.TOCHKA)
        )
        company_ids = list(result.scalars().all())

    if not company_ids:
        logger.info("scheduler: tochka balances — нет компаний с токеном")
        return

    total_saved = 0
    for cid in company_ids:
        try:
            async with async_session_maker() as session:
                saved = await get_balances(session, cid)
                await session.commit()
            total_saved += len(saved)
        except TochkaError as exc:
            logger.warning("tochka sync: company=%s skipped: %s", cid, exc)
        except Exception:  # noqa: BLE001
            logger.exception("tochka sync: company=%s failed", cid)

    logger.info(
        "scheduler: tochka balances — companies=%s, balances_saved=%s",
        len(company_ids),
        total_saved,
    )


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
    scheduler.add_job(
        job_tochka_balances,
        trigger=IntervalTrigger(hours=settings.TOCHKA_SYNC_INTERVAL_HOURS),
        id="tochka_balances",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info("APScheduler started with %s jobs", len(scheduler.get_jobs()))


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
