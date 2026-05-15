"""Интеграция с API Точки (OAuth2 + bank-accounts).

OAuth endpoints:
  authorize: https://id.tochka.com/oauth2/authorize
  token:     https://id.tochka.com/oauth2/token
API:
  base:      https://enter.tochka.com/api/v1
  accounts:  GET /bank-accounts/v1.0/accounts
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

AUTHORIZE_URL = "https://id.tochka.com/oauth2/authorize"
TOKEN_URL = "https://id.tochka.com/oauth2/token"
API_BASE = "https://enter.tochka.com/api/v1"
ACCOUNTS_PATH = "/bank-accounts/v1.0/accounts"

DEFAULT_SCOPE = "account_info balances statements"
HTTP_TIMEOUT = 20.0
REFRESH_LEEWAY = timedelta(minutes=5)


class TochkaError(Exception):
    pass


async def exchange_code_for_token(code: str) -> dict[str, Any]:
    """Обменять authorization code на access_token + refresh_token."""

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.TOCHKA_REDIRECT_URL,
        "client_id": settings.TOCHKA_CLIENT_ID,
        "client_secret": settings.TOCHKA_CLIENT_SECRET,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(TOKEN_URL, data=data)
    if r.status_code >= 400:
        raise TochkaError(f"token exchange failed: HTTP {r.status_code} {r.text[:300]}")
    return r.json()


async def upsert_token(
    db: AsyncSession,
    company_id: int,
    payload: dict[str, Any],
    scope: str | None = None,
) -> OAuthToken:
    """Сохранить (или обновить) токен Точки для компании."""

    expires_in = payload.get("expires_in")
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        if expires_in
        else None
    )

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
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_at=expires_at,
            scope=scope or payload.get("scope"),
        )
        db.add(token)
    else:
        existing.access_token = payload["access_token"]
        if payload.get("refresh_token"):
            existing.refresh_token = payload["refresh_token"]
        existing.expires_at = expires_at
        existing.scope = scope or payload.get("scope") or existing.scope
        token = existing
    await db.flush()
    return token


async def refresh_access_token(db: AsyncSession, token: OAuthToken) -> OAuthToken:
    if not token.refresh_token:
        raise TochkaError("no refresh_token available")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": token.refresh_token,
        "client_id": settings.TOCHKA_CLIENT_ID,
        "client_secret": settings.TOCHKA_CLIENT_SECRET,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(TOKEN_URL, data=data)
    if r.status_code >= 400:
        raise TochkaError(f"refresh failed: HTTP {r.status_code} {r.text[:300]}")
    payload = r.json()

    token.access_token = payload["access_token"]
    if payload.get("refresh_token"):
        token.refresh_token = payload["refresh_token"]
    expires_in = payload.get("expires_in")
    if expires_in:
        token.expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
    if payload.get("scope"):
        token.scope = payload["scope"]
    await db.flush()
    return token


async def _get_valid_token(db: AsyncSession, company_id: int) -> OAuthToken:
    token = await db.scalar(
        select(OAuthToken).where(
            OAuthToken.company_id == company_id,
            OAuthToken.bank == Bank.TOCHKA,
        )
    )
    if token is None:
        raise TochkaError(f"no Tochka token for company_id={company_id}")
    if token.expires_at is not None:
        if token.expires_at - REFRESH_LEEWAY <= datetime.now(timezone.utc):
            logger.info("tochka: refreshing token for company=%s", company_id)
            token = await refresh_access_token(db, token)
    return token


def _parse_account(item: dict[str, Any]) -> tuple[str | None, Decimal | None]:
    """Из ответа Точки достаём (номер счёта, остаток).

    Подстраиваемся под обе формы — Open Banking ("Data.Account[]") и плоский
    список — поэтому проверяем несколько ключей.
    """

    account_number = (
        item.get("accountId")
        or item.get("account_number")
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
        amount = Decimal(str(balance_raw))
    except Exception:  # noqa: BLE001
        return account_number, None
    return account_number, amount


async def get_balances(db: AsyncSession, company_id: int) -> list[Balance]:
    """Сходить в Точку, получить остатки и записать их в `balances`."""

    token = await _get_valid_token(db, company_id)

    async def _fetch(t: OAuthToken) -> httpx.Response:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            return await client.get(
                f"{API_BASE}{ACCOUNTS_PATH}",
                headers={"Authorization": f"Bearer {t.access_token}"},
            )

    r = await _fetch(token)
    if r.status_code == 401:
        # access_token истёк — пробуем refresh и повтор
        logger.info("tochka: 401 from accounts API, refreshing token")
        token = await refresh_access_token(db, token)
        r = await _fetch(token)
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
