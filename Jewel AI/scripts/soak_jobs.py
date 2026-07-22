#!/usr/bin/env python3
"""Sprint 1/4 load-soak baseline against a running API (staging).

Usage:
  BASE_URL=https://staging.example.com \
  EMAIL=studio@jewelai.com PASSWORD=... \
  python scripts/soak_jobs.py

Exit metric target: <5% app-side hard failure (exclude fal 5xx).
"""
from __future__ import annotations

import concurrent.futures
import os
import sys
import time
from typing import Any

import requests

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EMAIL = os.environ.get("EMAIL", "studio@jewelai.com")
PASSWORD = os.environ.get("PASSWORD", "studio123")
JOB_WORKERS = int(os.environ.get("JOB_WORKERS", "20"))
JOB_ROUNDS = int(os.environ.get("JOB_ROUNDS", "5"))
DURATION_SEC = int(os.environ.get("DURATION_SEC", "60"))


def login() -> str:
    r = requests.post(f"{BASE}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def create_job(token: str) -> dict[str, Any]:
    # Intentionally minimal — expects 400 without asset; counts transport/auth/DB health.
    # For full generation soak, set ASSET_ID.
    asset_id = os.environ.get("ASSET_ID")
    headers = {"Authorization": f"Bearer {token}"}
    body: dict[str, Any] = {"workflow": "CATALOG_IMAGE", "jewelry_type": "Ring"}
    if asset_id:
        body["asset_id"] = asset_id
    t0 = time.time()
    try:
        r = requests.post(f"{BASE}/api/jobs", json=body, headers=headers, timeout=60)
        return {
            "ok": r.status_code in (200, 201, 400, 402, 422, 429),
            "status": r.status_code,
            "ms": int((time.time() - t0) * 1000),
            "hard_fail": r.status_code >= 500,
        }
    except Exception as exc:
        return {"ok": False, "status": 0, "ms": int((time.time() - t0) * 1000), "hard_fail": True, "err": str(exc)}


def main() -> int:
    token = login()
    results: list[dict[str, Any]] = []
    asset_id = os.environ.get("ASSET_ID")
    if asset_id:
        print(
            "WARNING: ASSET_ID is set — each successful create will spend fal.ai credits.",
            file=sys.stderr,
        )
        host = BASE.lower()
        is_prodish = (
            "127.0.0.1" not in host
            and "localhost" not in host
            and (host.startswith("https://") or "railway.app" in host)
        )
        if is_prodish and os.environ.get("ALLOW_PROD_FAL_GENERATION", "").strip() != "1":
            print(
                "REFUSING soak with ASSET_ID against non-local API (fal credit burn).\n"
                "Set ALLOW_PROD_FAL_GENERATION=1 to override.",
                file=sys.stderr,
            )
            return 2
    deadline = time.time() + DURATION_SEC
    with concurrent.futures.ThreadPoolExecutor(max_workers=JOB_WORKERS) as pool:
        while time.time() < deadline:
            futs = [pool.submit(create_job, token) for _ in range(JOB_ROUNDS)]
            for f in concurrent.futures.as_completed(futs):
                results.append(f.result())

    total = len(results) or 1
    hard = sum(1 for r in results if r.get("hard_fail"))
    rate = hard / total
    print(f"requests={total} hard_fail={hard} rate={rate:.2%} avg_ms={sum(r['ms'] for r in results)/total:.0f}")
    print("TARGET: hard_fail rate < 5% (app/DB/Redis; exclude intentional 4xx)")
    return 0 if rate < 0.05 else 1


if __name__ == "__main__":
    sys.exit(main())
