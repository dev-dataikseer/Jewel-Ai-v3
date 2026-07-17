"""HTTP client for fal.ai Platform Billing API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.logging_config import get_logger

logger = get_logger(__name__)

BILLING_URL = "https://api.fal.ai/v1/account/billing"
REQUEST_TIMEOUT = 20.0


class FalBillingError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, error_type: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type


@dataclass(frozen=True)
class FalBillingSnapshot:
    username: str | None
    current_balance: float
    currency: str
    raw: dict[str, Any]


def fetch_account_billing(api_key: str) -> FalBillingSnapshot:
    """
    GET https://api.fal.ai/v1/account/billing?expand=credits

    Auth: Authorization: Key <FAL_KEY>
    """
    if not api_key or not api_key.strip():
        raise FalBillingError("FAL API key is not configured", error_type="authorization_error")

    headers = {"Authorization": f"Key {api_key.strip()}", "Accept": "application/json"}
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(BILLING_URL, params={"expand": "credits"}, headers=headers)
    except httpx.TimeoutException as exc:
        raise FalBillingError("fal.ai billing request timed out", error_type="server_error") from exc
    except httpx.HTTPError as exc:
        raise FalBillingError(f"fal.ai billing network error: {exc}", error_type="server_error") from exc

    if resp.status_code == 401:
        raise FalBillingError("fal.ai billing authentication failed", status_code=401, error_type="authorization_error")
    if resp.status_code == 403:
        raise FalBillingError("fal.ai billing access denied", status_code=403, error_type="authorization_error")
    if resp.status_code == 429:
        raise FalBillingError("fal.ai billing rate limited", status_code=429, error_type="rate_limited")
    if resp.status_code >= 400:
        detail = _error_message(resp)
        raise FalBillingError(
            detail or f"fal.ai billing error ({resp.status_code})",
            status_code=resp.status_code,
            error_type="server_error",
        )

    try:
        payload = resp.json()
    except Exception as exc:
        raise FalBillingError("Invalid JSON from fal.ai billing", error_type="server_error") from exc

    if not isinstance(payload, dict):
        raise FalBillingError("Unexpected fal.ai billing response shape", error_type="server_error")

    credits = payload.get("credits")
    if not isinstance(credits, dict):
        raise FalBillingError(
            "Credits missing from billing response — ensure expand=credits",
            error_type="validation_error",
        )

    try:
        balance = float(credits["current_balance"])
        currency = str(credits.get("currency") or "USD")
    except (KeyError, TypeError, ValueError) as exc:
        raise FalBillingError("Malformed credits object in billing response", error_type="validation_error") from exc

    return FalBillingSnapshot(
        username=str(payload["username"]) if payload.get("username") is not None else None,
        current_balance=balance,
        currency=currency,
        raw=payload,
    )


def _error_message(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])
    except Exception:
        pass
    return (resp.text or "")[:240]
