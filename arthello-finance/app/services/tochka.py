"""Точка Open Banking — реальная схема интеграции.

Документация: https://enter.tochka.com/uapi/open-banking/v1.0/docs

Поток:
  1. client_credentials → "app-token" (для админских операций)
  2. POST /uapi/v1.0/consents с app-token → consent_id
  3. Редирект пользователя на /connect/authorize?...&consent_id=...
  4. Callback с ?code → POST /connect/token grant_type=authorization_code
     → access_token (24ч) + refresh_token (30 дней) пользователя
  5. При истечении access_token → POST /connect/token grant_type=refresh_token

User-токен хранится в oauth_tokens по (company_id, bank=TOCHKA).
App-токен не сохраняем — он короткоживущий, запрашивается на лету
при создании consent'а.
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

CONSENTS_PATH = "/consents"
ACCOUNTS_PATH = "/accounts"
HTTP_TIMEOUT = 20.0
REFRESH_LEEWAY = timedelta(minutes=2)

DEFAULT_PERMISSIONS: list[str] = [
    "ReadAccountsBasic",
    "ReadAccountsDetail",
    "ReadBalances",
    "ReadStatements",
    "ReadCustomerData",
]


class TochkaError(Exception):
    pass


def _is_configured() -> bool:
    return bool(settings.TOCHKA_CLIENT_ID and settings.TOCHKA_CLIENT_SECRET)


# ─── ШАГ 1 — client_credentials app-token ────────────────────────────────────


async def get_app_token() -> str:
    """ШАГ 1. POST /connect/token grant_type=client_credentials → app access_token."""

    if not _is_configured():
        raise TochkaError("TOCHKA_CLIENT_ID / TOCHKA_CLIENT_SECRET are not set")

    data = {
        "grant_type": "client_credentials",
        "client_id": settings.TOCHKA_CLIENT_ID,
        "client_secret": settings.TOCHKA_CLIENT_SECRET,
        "scope": settings.TOCHKA_SCOPE,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(
            settings.TOCHKA_TOKEN_URL,
            data=data,
            headers={"Accept": "application/json"},
        )
    if r.status_code >= 400:
        raise TochkaError(
            f"client_credentials failed: HTTP {r.status_code}: {r.text[:500]}"
        )
    try:
        payload = r.json()
    except ValueError as exc:
        raise TochkaError(f"non-JSON from token endpoint: {r.text[:500]}") from exc
    token = payload.get("access_token")
    if not token:
        raise TochkaError(f"no access_token in payload: {payload}")
    return token


# ─── ШАГ 2 — создать consent ─────────────────────────────────────────────────


async def create_consent(
    app_token: str, permissions: list[str] | None = None
) -> str:
    """ШАГ 2. POST /uapi/v1.0/consents с app_token → consent_id."""

    body: dict[str, Any] = {
        "Data": {"permissions": permissions or DEFAULT_PERMISSIONS}
    }
    url = f"{settings.TOCHKA_API_BASE}{CONSENTS_PATH}"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {app_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
    if r.status_code >= 400:
        raise TochkaError(f"consents API HTTP {r.status_code}: {r.text[:500]}")
    try:
        data = r.json()
    except ValueError as exc:
        raise TochkaError(f"non-JSON from consents: {r.text[:500]}") from exc

    consent_id = (
        (data.get("Data") or {}).get("consentId")
        or (data.get("Data") or {}).get("consent_id")
        or data.get("consentId")
        or data.get("consent_id")
    )
    if not consent_id:
        raise TochkaError(f"no consentId in response: {data}")
    return str(consent_id)


# ─── ШАГ 4 — обмен code на пользовательский токен ────────────────────────────


async def exchange_code_for_token(code: str) -> dict[str, Any]:
    """ШАГ 4. POST /connect/token grant_type=authorization_code → access+refresh."""

    if not _is_configured():
        raise TochkaError("TOCHKA_CLIENT_ID / TOCHKA_CLIENT_SECRET are not set")

    data = {
        "grant_type": "authorization_code",
        "client_id": settings.TOCHKA_CLIENT_ID,
        "client_secret": settings.TOCHKA_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.TOCHKA_REDIRECT_URL,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(
            settings.TOCHKA_TOKEN_URL,
            data=data,
            headers={"Accept": "application/json"},
        )
    if r.status_code >= 400:
        raise TochkaError(
            f"authorization_code exchange failed: HTTP {r.status_code}: {r.text[:500]}"
        )
    return r.json()


# ─── ШАГ 5 — refresh_token ───────────────────────────────────────────────────


async def refresh_user_token(db: AsyncSession, token: OAuthToken) -> OAuthToken:
    """ШАГ 5. POST /connect/token grant_type=refresh_token → новый access+refresh."""

    if not token.refresh_token:
        raise TochkaError("no refresh_token stored — needs re-authorization")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": token.refresh_token,
        "client_id": settings.TOCHKA_CLIENT_ID,
        "client_secret": settings.TOCHKA_CLIENT_SECRET,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(
            settings.TOCHKA_TOKEN_URL,
            data=data,
            headers={"Accept": "application/json"},
        )
    if r.status_code >= 400:
        raise TochkaError(f"refresh failed: HTTP {r.status_code}: {r.text[:500]}")
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


# ─── upsert и доступ к токену пользователя ───────────────────────────────────


async def upsert_user_token(
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
    refresh_token = payload.get("refresh_token")

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
            refresh_token=refresh_token,
            expires_at=expires_at,
            scope=scope,
        )
        db.add(token)
    else:
        existing.access_token = access_token
        if refresh_token:
            existing.refresh_token = refresh_token
        existing.expires_at = expires_at
        existing.scope = scope
        token = existing
    await db.flush()
    return token


async def _get_valid_user_token(db: AsyncSession, company_id: int) -> OAuthToken:
    token = await db.scalar(
        select(OAuthToken).where(
            OAuthToken.company_id == company_id,
            OAuthToken.bank == Bank.TOCHKA,
        )
    )
    if token is None:
        raise TochkaError(
            f"no Tochka token for company_id={company_id}; "
            "visit /api/auth/tochka/login first"
        )
    if (
        token.expires_at is not None
        and token.expires_at - REFRESH_LEEWAY <= datetime.now(timezone.utc)
    ):
        logger.info("tochka: access_token expired for company=%s, refreshing", company_id)
        token = await refresh_user_token(db, token)
    return token


# ─── работа с балансами ──────────────────────────────────────────────────────


def _parse_account(item: dict[str, Any]) -> tuple[str | None, Decimal | None]:
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
    """GET /accounts с user-токеном. На 401 рефрешим и повторяем."""

    token = await _get_valid_user_token(db, company_id)

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
        logger.info("tochka: 401 from /accounts, refreshing user token")
        token = await refresh_user_token(db, token)
        r = await _do(token)
    return r


async def get_balances(db: AsyncSession, company_id: int) -> list[Balance]:
    """Сходить в Точку, получить остатки и записать их в `balances`."""

    r = await fetch_accounts_raw(db, company_id)
    if r.status_code >= 400:
        raise TochkaError(f"accounts API failed: HTTP {r.status_code} {r.text[:300]}")

    payload = r.json()
    items: list[dict[str, Any]] = (
        (payload.get("Data") or {}).get("Account")
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
