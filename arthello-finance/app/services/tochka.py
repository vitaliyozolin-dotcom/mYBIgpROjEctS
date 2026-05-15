"""Интеграция с Точка API — Open Banking v1.0, Client Credentials Flow.

Поток:
1. POST {TOCHKA_TOKEN_URL} с grant_type=client_credentials, client_id,
   client_secret, scope.
2. В ответ access_token (Bearer) + expires_in.
3. Дальнейшие запросы к API_BASE/accounts со заголовком
   Authorization: Bearer <token>.

Токен сохраняем в таблицу oauth_tokens на (company_id, bank=TOCHKA), чтобы
ассоциировать с конкретной компанией. Реальные креды (client_id/secret)
у нас общие — это просто способ держать живой Bearer и знать, когда обновить.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.account import Account, Bank
from app.models.balance import Balance, BalanceSource
from app.models.oauth_token import OAuthToken

logger = logging.getLogger(__name__)

ACCOUNTS_PATH = "/accounts"
HTTP_TIMEOUT = 20.0
REFRESH_LEEWAY = timedelta(minutes=2)


class TochkaError(Exception):
    pass


def _is_configured() -> bool:
    return bool(settings.TOCHKA_CLIENT_ID and settings.TOCHKA_CLIENT_SECRET)


def _is_token_alive(token: OAuthToken | None) -> bool:
    if token is None or not token.access_token:
        return False
    if token.expires_at is None:
        return False
    return token.expires_at - REFRESH_LEEWAY > datetime.now(timezone.utc)


async def _request_new_token() -> dict[str, Any]:
    """POST на token endpoint Точки с grant_type=client_credentials."""

    if not _is_configured():
        raise TochkaError("TOCHKA_CLIENT_ID / TOCHKA_CLIENT_SECRET are not set")

    data = {
        "grant_type": "client_credentials",
        "client_id": settings.TOCHKA_CLIENT_ID,
        "client_secret": settings.TOCHKA_CLIENT_SECRET,
        "scope": settings.TOCHKA_SCOPE,
    }
    headers = {"Accept": "application/json"}
    logger.info("tochka: requesting client_credentials token, scope=%r", settings.TOCHKA_SCOPE)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(settings.TOCHKA_TOKEN_URL, data=data, headers=headers)

    if r.status_code >= 400:
        raise TochkaError(
            f"token endpoint returned HTTP {r.status_code}: {r.text[:500]}"
        )
    try:
        return r.json()
    except ValueError as exc:
        raise TochkaError(f"token endpoint returned non-JSON: {r.text[:500]}") from exc


async def _upsert_token(
    db: AsyncSession, company_id: int, payload: dict[str, Any]
) -> OAuthToken:
    access_token = payload.get("access_token")
    if not access_token:
        raise TochkaError(f"no access_token in payload: {payload}")

    expires_in = payload.get("expires_in")
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        if expires_in
        else None
    )
    scope = payload.get("scope") or settings.TOCHKA_SCOPE

    existing = await db.scalar(
        select(OAuthToken).where(
            OAuthToken.company_id == company_id,
            OAuthToken.bank == Bank.TOCHKA,
        )
    )
    if existing is None:
        token = OAuthToken(
            company_id=company_id,
            bank=Bank.TOCHKA,
            access_token=access_token,
            refresh_token=None,  # client_credentials не выдаёт refresh_token
            expires_at=expires_at,
            scope=scope,
        )
        db.add(token)
    else:
        existing.access_token = access_token
        existing.refresh_token = None
        existing.expires_at = expires_at
        existing.scope = scope
        token = existing
    await db.flush()
    return token


async def get_or_refresh_token(db: AsyncSession, company_id: int) -> OAuthToken:
    """Вернуть живой токен для компании, обновив при необходимости.

    Если в БД лежит токен с expires_at в будущем (с запасом REFRESH_LEEWAY) —
    отдаём его. Иначе запрашиваем новый client_credentials-токен у Точки и
    апсертим.
    """

    existing = await db.scalar(
        select(OAuthToken).where(
            OAuthToken.company_id == company_id,
            OAuthToken.bank == Bank.TOCHKA,
        )
    )
    if _is_token_alive(existing):
        return existing

    payload = await _request_new_token()
    return await _upsert_token(db, company_id, payload)


def _parse_account(item: dict[str, Any]) -> tuple[str | None, Decimal | None]:
    """Достать (account_number, amount) из элемента ответа Точки.

    Open Banking-форма у Точки нестабильна — пробуем несколько ключей.
    """

    account_number = (
        item.get("accountId")
        or item.get("account_number")
        or item.get("accountCode")
        or item.get("nominalAccountCode")
        or item.get("number")
    )
    balance_raw: Any = None
    bal = item.get("balance")
    if isinstance(bal, dict):
        balance_raw = bal.get("value") or bal.get("amount")
    elif bal is not None:
        balance_raw = bal
    if balance_raw is None:
        amounts = item.get("Amount") or item.get("amounts")
        if isinstance(amounts, list) and amounts:
            balance_raw = amounts[0].get("amount") or amounts[0].get("value")

    if balance_raw is None:
        return account_number, None
    try:
        return account_number, Decimal(str(balance_raw))
    except Exception:  # noqa: BLE001
        return account_number, None


async def fetch_accounts_raw(db: AsyncSession, company_id: int) -> httpx.Response:
    """Сходить в /accounts с токеном company_id и вернуть сырой Response.

    На 401 обновляет токен (запрашивает новый client_credentials) и повторяет.
    """

    token = await get_or_refresh_token(db, company_id)

    async def _do(t: OAuthToken) -> httpx.Response:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            return await client.get(
                f"{settings.TOCHKA_API_BASE}{ACCOUNTS_PATH}",
                headers={
                    "Authorization": f"Bearer {t.access_token}",
                    "Accept": "application/json",
                },
            )

    r = await _do(token)
    if r.status_code == 401:
        logger.info("tochka: 401 from /accounts, requesting fresh token")
        payload = await _request_new_token()
        token = await _upsert_token(db, company_id, payload)
        r = await _do(token)
    return r


async def get_balances(db: AsyncSession, company_id: int) -> list[Balance]:
    """Сходить в Точку, получить остатки и записать их в `balances`."""

    r = await fetch_accounts_raw(db, company_id)
    if r.status_code >= 400:
        raise TochkaError(f"accounts API failed: HTTP {r.status_code} {r.text[:300]}")

    payload = r.json()
    items: list[dict[str, Any]] = (
        payload.get("Data", {}).get("Account")
        or payload.get("accounts")
        or payload.get("data")
        or []
    )

    saved: list[Balance] = []
    for item in items:
        account_number, amount = _parse_account(item)
        if not account_number or amount is None:
            continue
        db_account = await db.scalar(
            select(Account).where(
                Account.company_id == company_id,
                Account.account_number == account_number,
            )
        )
        if db_account is None:
            logger.warning(
                "tochka: account %s not found in DB for company=%s",
                account_number,
                company_id,
            )
            continue
        b = Balance(
            account_id=db_account.id,
            amount=amount,
            currency="RUB",
            source=BalanceSource.API,
        )
        db.add(b)
        saved.append(b)

    await db.flush()
    logger.info(
        "tochka: company=%s, accounts in payload=%s, balances saved=%s",
        company_id,
        len(items),
        len(saved),
    )
    return saved
