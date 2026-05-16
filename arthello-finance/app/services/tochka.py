"""Точка Open Banking — реальный flow.

Документация: developers.tochka.com

Endpoints:
  Token:      POST https://enter.tochka.com/connect/token
  Authorize:  GET  https://enter.tochka.com/connect/authorize
  Consents:   POST https://enter.tochka.com/uapi/v1.0/consents
  Balances:   GET  https://enter.tochka.com/uapi/open-banking/v1.0/balances
  (per acc:   GET  .../uapi/open-banking/v1.0/accounts/{accountId}/balances)

3 шага:
  1. /login   — client_credentials → consent → редирект на /connect/authorize
  2. /callback — обмен code на access+refresh
  3. get_balances — GET /balances с user-токеном, парсит Data.Balance[]
     с type=OpeningAvailable как текущий остаток
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

BALANCES_PATH = "/balances"
HTTP_TIMEOUT = 20.0
# Рефрешим access_token если до его истечения осталось < 2 часов.
REFRESH_LEEWAY = timedelta(hours=2)

DEFAULT_PERMISSIONS: list[str] = [
    "ReadAccountsBasic",
    "ReadAccountsDetail",
    "ReadBalances",
    "ReadStatements",
    "ReadCustomerData",
]

# Тип записи Balance, который считаем "текущим остатком".
CURRENT_BALANCE_TYPE = "OpeningAvailable"


class TochkaError(Exception):
    pass


def _is_configured() -> bool:
    return bool(settings.TOCHKA_CLIENT_ID and settings.TOCHKA_CLIENT_SECRET)


# ─── ШАГ 1a — client_credentials app-токен ───────────────────────────────────


async def get_app_token() -> str:
    """POST /connect/token grant_type=client_credentials → app access_token."""

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


# ─── ШАГ 1b — создать consent ────────────────────────────────────────────────


async def create_consent(
    app_token: str, permissions: list[str] | None = None
) -> str:
    """POST {TOCHKA_CONSENTS_URL} с app_token → consent_id."""

    body: dict[str, Any] = {
        "Data": {"permissions": permissions or DEFAULT_PERMISSIONS}
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(
            settings.TOCHKA_CONSENTS_URL,
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


# ─── ШАГ 2 — обмен code на user-токен ────────────────────────────────────────


async def exchange_code_for_token(code: str) -> dict[str, Any]:
    """POST /connect/token grant_type=authorization_code → access+refresh."""

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


# ─── refresh_token ───────────────────────────────────────────────────────────


async def refresh_user_token(db: AsyncSession, token: OAuthToken) -> OAuthToken:
    """POST /connect/token grant_type=refresh_token → новый access+refresh."""

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
    # Рефрешим, если осталось меньше REFRESH_LEEWAY (2 часа) до истечения.
    if (
        token.expires_at is not None
        and token.expires_at - REFRESH_LEEWAY <= datetime.now(timezone.utc)
    ):
        logger.info(
            "tochka: access_token expiring soon for company=%s (%s), refreshing",
            company_id,
            token.expires_at.isoformat() if token.expires_at else "?",
        )
        token = await refresh_user_token(db, token)
    return token


# ─── ШАГ 3 — балансы ─────────────────────────────────────────────────────────


def _parse_balance_amount(item: dict[str, Any]) -> Decimal | None:
    """Достать Amount.Amount из элемента Balance. Учитывает creditDebitIndicator."""

    amount_obj = item.get("Amount") or item.get("amount") or {}
    if not isinstance(amount_obj, dict):
        return None
    raw = amount_obj.get("Amount") or amount_obj.get("amount") or amount_obj.get("value")
    if raw is None:
        return None
    try:
        value = Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return None

    indicator = item.get("creditDebitIndicator") or item.get("CreditDebitIndicator")
    if isinstance(indicator, str) and indicator.lower() == "debit":
        value = -value
    return value


async def fetch_balances_raw(db: AsyncSession, company_id: int) -> httpx.Response:
    """GET {API_BASE}/balances с user-токеном. На 401 рефрешим и повторяем."""

    token = await _get_valid_user_token(db, company_id)

    async def _do(t: OAuthToken) -> httpx.Response:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            return await client.get(
                f"{settings.TOCHKA_API_BASE}{BALANCES_PATH}",
                headers={
                    "Authorization": f"Bearer {t.access_token}",
                    "Accept": "application/json",
                },
            )

    r = await _do(token)
    if r.status_code == 401:
        logger.info("tochka: 401 from /balances, refreshing user token")
        token = await refresh_user_token(db, token)
        r = await _do(token)
    return r


async def get_balances(db: AsyncSession, company_id: int) -> list[Balance]:
    """GET /balances → парсим Data.Balance[] с type=OpeningAvailable → balances."""

    r = await fetch_balances_raw(db, company_id)
    if r.status_code >= 400:
        raise TochkaError(f"/balances HTTP {r.status_code} {r.text[:300]}")

    payload = r.json()
    items: list[dict[str, Any]] = (
        (payload.get("Data") or {}).get("Balance")
        or (payload.get("Data") or {}).get("balance")
        or payload.get("balances")
        or []
    )

    saved: list[Balance] = []
    skipped_no_match: list[str] = []
    for item in items:
        item_type = item.get("type") or item.get("Type")
        if item_type != CURRENT_BALANCE_TYPE:
            continue

        account_id = item.get("accountId") or item.get("AccountId")
        amount = _parse_balance_amount(item)
        if not account_id or amount is None:
            continue

        amount_obj = item.get("Amount") or {}
        currency = (
            amount_obj.get("Currency") if isinstance(amount_obj, dict) else None
        ) or "RUB"

        db_account = await db.scalar(
            select(Account).where(
                Account.company_id == company_id,
                Account.account_number == account_id,
            )
        )
        if db_account is None:
            skipped_no_match.append(account_id)
            continue

        b = Balance(
            account_id=db_account.id,
            amount=amount,
            currency=currency,
            source=BalanceSource.API,
        )
        db.add(b)
        saved.append(b)

    await db.flush()
    logger.info(
        "tochka: company=%s, items=%s, saved=%s, no_match=%s",
        company_id,
        len(items),
        len(saved),
        skipped_no_match,
    )
    return saved
