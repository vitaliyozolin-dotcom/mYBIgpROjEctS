"""Синхронизация с банками (Точка, Тбанк, Альфа).

Каркас интеграции: для каждого активного счёта запрашивается выписка через
API конкретного банка, новые транзакции идемпотентно сохраняются по
`external_id`, а актуальный остаток добавляется в `balances`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.database import async_session_maker
from app.models.account import Account
from app.models.balance import Balance, BalanceSource
from app.models.transaction import Transaction, TransactionDirection

logger = logging.getLogger(__name__)


class BankSyncError(Exception):
    pass


async def fetch_account_statement(account: Account) -> tuple[list[dict], Decimal | None]:
    """Запросить выписку и текущий остаток у банка.

    Возвращает кортеж (transactions, balance). Каркас — реальный код
    подключается по API конкретного банка (Точка / Тбанк / Альфа).
    """

    logger.info(
        "bank_sync: fetch statement for account=%s bank=%s (stub)",
        account.id,
        account.bank.value,
    )
    return [], None


async def _persist(account: Account, items: list[dict], balance: Decimal | None) -> int:
    added = 0
    async with async_session_maker() as session:
        for item in items:
            external_id = item["external_id"]
            existing = await session.execute(
                select(Transaction).where(Transaction.external_id == external_id)
            )
            if existing.scalar_one_or_none() is not None:
                continue
            tx = Transaction(
                account_id=account.id,
                external_id=external_id,
                amount=Decimal(str(item["amount"])),
                direction=TransactionDirection(item["direction"]),
                counterparty=item.get("counterparty"),
                purpose=item.get("purpose"),
                dds_category=item.get("dds_category"),
                transaction_date=item.get("transaction_date", datetime.now(timezone.utc)),
            )
            session.add(tx)
            added += 1

        if balance is not None:
            session.add(
                Balance(
                    account_id=account.id,
                    amount=balance,
                    source=BalanceSource.API,
                )
            )

        await session.commit()
    return added


async def sync_account(account_id: int) -> int:
    async with async_session_maker() as session:
        account = await session.get(Account, account_id)
    if account is None:
        raise BankSyncError(f"Account {account_id} not found")
    items, balance = await fetch_account_statement(account)
    added = await _persist(account, items, balance)
    logger.info("bank_sync: account=%s synced, %s new transactions", account_id, added)
    return added


async def sync_all_accounts() -> dict:
    async with async_session_maker() as session:
        result = await session.execute(select(Account).where(Account.is_active.is_(True)))
        accounts = result.scalars().all()

    total_added = 0
    errors: list[str] = []
    for account in accounts:
        try:
            items, balance = await fetch_account_statement(account)
            total_added += await _persist(account, items, balance)
        except Exception as exc:  # noqa: BLE001
            logger.exception("bank_sync failed for account %s", account.id)
            errors.append(f"account={account.id}: {exc}")

    return {
        "accounts_processed": len(accounts),
        "transactions_added": total_added,
        "errors": errors,
    }
