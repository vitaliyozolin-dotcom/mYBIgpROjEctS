"""Синхронизация с банками.

Сейчас содержит каркас и плейсхолдеры для интеграций. Реальные клиенты банков
(Тинькофф, Альфа, Сбер) подключаются по их API. Метод `sync_all_accounts`
вызывается из APScheduler.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.database import async_session_maker
from app.models.account import Account
from app.models.transaction import Transaction, TransactionKind

logger = logging.getLogger(__name__)


class BankSyncError(Exception):
    pass


async def fetch_account_statement(account: Account) -> list[dict]:
    """Запросить выписку у банка для конкретного счёта.

    Возвращает список словарей с полями: external_id, kind, amount, currency,
    counterparty, counterparty_inn, description, occurred_at, balance_after.

    В этом каркасе ничего не запрашивает — реализуется по API конкретного банка.
    """

    logger.info(
        "bank_sync: fetch statement for account=%s bank=%s (stub)",
        account.id,
        account.bank_name,
    )
    return []


async def _upsert_transactions(account: Account, items: list[dict]) -> int:
    if not items:
        return 0
    added = 0
    async with async_session_maker() as session:
        for item in items:
            external_id = item.get("external_id")
            if external_id:
                existing = await session.execute(
                    select(Transaction).where(Transaction.external_id == external_id)
                )
                if existing.scalar_one_or_none() is not None:
                    continue

            tx = Transaction(
                account_id=account.id,
                external_id=external_id,
                kind=TransactionKind(item.get("kind", "debit")),
                amount=Decimal(str(item["amount"])),
                currency=item.get("currency", account.currency),
                balance_after=(
                    Decimal(str(item["balance_after"]))
                    if item.get("balance_after") is not None
                    else None
                ),
                counterparty=item.get("counterparty"),
                counterparty_inn=item.get("counterparty_inn"),
                description=item.get("description"),
                occurred_at=item.get("occurred_at", datetime.now(timezone.utc)),
            )
            session.add(tx)
            added += 1

            if tx.balance_after is not None:
                acc = await session.get(Account, account.id)
                if acc:
                    acc.balance = tx.balance_after

        await session.commit()
    return added


async def sync_account(account_id: int) -> int:
    async with async_session_maker() as session:
        account = await session.get(Account, account_id)
    if account is None:
        raise BankSyncError(f"Account {account_id} not found")

    items = await fetch_account_statement(account)
    added = await _upsert_transactions(account, items)
    logger.info("bank_sync: account=%s synced, %s new transactions", account_id, added)
    return added


async def sync_all_accounts() -> dict:
    """Синхронизировать все активные счета. Вызывается из планировщика."""

    async with async_session_maker() as session:
        result = await session.execute(select(Account).where(Account.is_active.is_(True)))
        accounts = result.scalars().all()

    total_added = 0
    errors: list[str] = []
    for account in accounts:
        try:
            items = await fetch_account_statement(account)
            total_added += await _upsert_transactions(account, items)
        except Exception as exc:  # noqa: BLE001
            logger.exception("bank_sync failed for account %s", account.id)
            errors.append(f"account={account.id}: {exc}")

    return {
        "accounts_processed": len(accounts),
        "transactions_added": total_added,
        "errors": errors,
    }
