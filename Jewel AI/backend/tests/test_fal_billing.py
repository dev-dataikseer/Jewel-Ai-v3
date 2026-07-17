"""Unit tests for fal billing client parsing (no live network)."""

from unittest.mock import MagicMock, patch

import pytest

from app.providers.fal_billing.client import FalBillingError, fetch_account_billing
from app.providers.fal_billing.service import _view_from_cache


def test_fetch_account_billing_parses_credits():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "username": "my-team",
        "credits": {"current_balance": 24.5, "currency": "USD"},
    }

    with patch("app.providers.fal_billing.client.httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.get.return_value = mock_resp
        snap = fetch_account_billing("test-key")

    assert snap.current_balance == 24.5
    assert snap.currency == "USD"
    assert snap.username == "my-team"
    client.get.assert_called_once()
    args, kwargs = client.get.call_args
    assert kwargs["params"] == {"expand": "credits"}
    assert kwargs["headers"]["Authorization"] == "Key test-key"


def test_fetch_account_billing_requires_key():
    with pytest.raises(FalBillingError):
        fetch_account_billing("")


def test_view_from_cache_low_balance():
    view = _view_from_cache(
        {"current_balance": 3.2, "currency": "USD", "updated_at": "2026-01-01T00:00:00+00:00"},
        threshold=5.0,
        stale=False,
    )
    assert view["available"] is True
    assert view["low_balance"] is True
    assert view["current_balance"] == 3.2
