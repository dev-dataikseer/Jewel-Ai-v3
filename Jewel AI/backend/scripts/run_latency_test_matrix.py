"""Controlled latency test matrix against production API (runs A–E as feasible).

Requires: BASE_URL, EMAIL, PASSWORD. Optional ASSET_ID to skip upload.
Writes results to scripts/_latency_test_matrix.json
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EMAIL = os.environ.get("EMAIL", "studio@jewelai.com")
PASSWORD = os.environ.get("PASSWORD", "studio123")
OUT = Path(__file__).resolve().parent / "_latency_test_matrix.json"


def _assert_generation_allowed() -> None:
    """Refuse to burn fal credits on production unless explicitly opted in."""
    host = BASE.lower()
    is_prodish = any(
        x in host
        for x in ("railway.app", "jewel-ai", "https://")
    ) and "127.0.0.1" not in host and "localhost" not in host
    if is_prodish and os.environ.get("ALLOW_PROD_FAL_GENERATION", "").strip() != "1":
        print(
            "REFUSING to create generation jobs against production.\n"
            f"  BASE_URL={BASE}\n"
            "This script spends fal.ai credits. Re-run only if you intend to:\n"
            "  ALLOW_PROD_FAL_GENERATION=1 BASE_URL=... python scripts/run_latency_test_matrix.py\n"
            "Prefer local: BASE_URL=http://127.0.0.1:8000",
            file=sys.stderr,
        )
        raise SystemExit(2)

# 1x1 JPEG
TINY_JPEG = bytes(
    [
        0xFF,
        0xD8,
        0xFF,
        0xE0,
        0x00,
        0x10,
        0x4A,
        0x46,
        0x49,
        0x46,
        0x00,
        0x01,
        0x01,
        0x00,
        0x00,
        0x01,
        0x00,
        0x01,
        0x00,
        0x00,
        0xFF,
        0xDB,
        0x00,
        0x43,
        0x00,
        0x08,
        0x06,
        0x06,
        0x07,
        0x06,
        0x05,
        0x08,
        0x07,
        0x07,
        0x07,
        0x09,
        0x09,
        0x08,
        0x0A,
        0x0C,
        0x14,
        0x0D,
        0x0C,
        0x0B,
        0x0B,
        0x0C,
        0x19,
        0x12,
        0x13,
        0x0F,
        0x14,
        0x1D,
        0x1A,
        0x1F,
        0x1E,
        0x1D,
        0x1A,
        0x1C,
        0x1C,
        0x20,
        0x24,
        0x2E,
        0x27,
        0x20,
        0x22,
        0x2C,
        0x23,
        0x1C,
        0x1C,
        0x28,
        0x37,
        0x29,
        0x2C,
        0x30,
        0x31,
        0x34,
        0x34,
        0x34,
        0x1F,
        0x27,
        0x39,
        0x3D,
        0x38,
        0x32,
        0x3C,
        0x2E,
        0x33,
        0x34,
        0x32,
        0xFF,
        0xC0,
        0x00,
        0x0B,
        0x08,
        0x00,
        0x01,
        0x00,
        0x01,
        0x01,
        0x01,
        0x11,
        0x00,
        0xFF,
        0xC4,
        0x00,
        0x14,
        0x00,
        0x01,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x03,
        0xFF,
        0xC4,
        0x00,
        0x14,
        0x10,
        0x01,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0xFF,
        0xDA,
        0x00,
        0x08,
        0x01,
        0x01,
        0x00,
        0x00,
        0x3F,
        0x00,
        0x37,
        0xFF,
        0xD9,
    ]
)


def _json_request(method: str, url: str, *, token: str | None = None, body: dict | None = None, timeout: int = 60):
    data = None
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {"detail": raw}
        except json.JSONDecodeError:
            payload = {"detail": raw[:500]}
        return exc.code, payload


def login() -> str:
    status, data = _json_request(
        "POST",
        f"{BASE}/api/auth/login",
        body={"email": EMAIL, "password": PASSWORD},
    )
    if status >= 400:
        raise RuntimeError(f"login failed {status}: {data}")
    return data["access_token"]


def upload_asset(token: str) -> tuple[str, int | None]:
    import uuid

    boundary = f"----jewel{uuid.uuid4().hex}"
    url = os.environ.get("ASSET_URL")
    if url:
        with urllib.request.urlopen(url, timeout=60) as resp:
            blob = resp.read()
        filename = "product.jpg"
    else:
        blob = TINY_JPEG
        filename = "tiny.jpg"

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + blob + f"\r\n--{boundary}--\r\n".encode("utf-8")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "application/json",
    }
    req = urllib.request.Request(f"{BASE}/api/assets/upload", data=body, headers=headers, method="POST")
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    upload_ms = int((time.perf_counter() - t0) * 1000)
    return data["id"], data.get("upload_ms") or upload_ms


def create_and_wait(token: str, body: dict, timeout_s: int = 600) -> dict:
    t0 = time.perf_counter()
    status, job = _json_request("POST", f"{BASE}/api/jobs", token=token, body=body, timeout=60)
    create_ms = int((time.perf_counter() - t0) * 1000)
    if status >= 400:
        return {"ok": False, "status": status, "detail": job, "create_ms": create_ms}
    job_id = job["id"]
    deadline = time.time() + timeout_s
    last = job
    while time.time() < deadline:
        time.sleep(3)
        st, last = _json_request("GET", f"{BASE}/api/jobs/{job_id}", token=token, timeout=30)
        if st >= 400:
            return {"ok": False, "status": st, "detail": last, "job_id": job_id, "create_ms": create_ms}
        if last.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
            break
    meta = last.get("provider_metadata") or {}
    return {
        "ok": last.get("status") == "COMPLETED",
        "job_id": job_id,
        "status": last.get("status"),
        "create_ms": create_ms,
        "wall_ms": int((time.perf_counter() - t0) * 1000),
        "model": last.get("provider_model") or meta.get("modelEndpointId"),
        "fal_request_id": meta.get("fal_request_id"),
        "fal_inference_time": meta.get("fal_inference_time"),
        "durationSplits": meta.get("durationSplits"),
        "latencyTrace": meta.get("latencyTrace"),
        "timing": (meta.get("timing") or {}),
        "error": last.get("error_message"),
    }


def main() -> int:
    _assert_generation_allowed()
    token = login()
    asset_id = os.environ.get("ASSET_ID")
    upload_ms = None
    if not asset_id:
        # Prefer reusing a real product image URL from env
        asset_id, upload_ms = upload_asset(token)

    runs = [
        {
            "id": "A",
            "purpose": "warm_baseline",
            "body": {
                "workflow": "CATALOG_IMAGE",
                "jewelry_type": "Ring",
                "asset_id": asset_id,
                "model_endpoint_id": "fal-ai/nano-banana-pro/edit",
            },
        },
        {
            "id": "D",
            "purpose": "prompt_weight",
            "body": {
                "workflow": "CATALOG_IMAGE",
                "jewelry_type": "Ring",
                "asset_id": asset_id,
                "model_endpoint_id": "fal-ai/nano-banana-pro/edit",
                "prompt_text": (
                    "warmer lighting, soft reflections, minimal props, clean white backdrop, "
                    "subtle luxury mood, keep jewelry identity locked exactly as product image"
                ),
            },
        },
        {
            "id": "E",
            "purpose": "alternate_model",
            "body": {
                "workflow": "CATALOG_IMAGE",
                "jewelry_type": "Ring",
                "asset_id": asset_id,
                "model_endpoint_id": "openai/gpt-image-2/edit",
            },
        },
    ]

    # Optional: only run subset
    only = os.environ.get("RUN_ONLY", "A")
    if only.upper() != "ALL":
        runs = [r for r in runs if r["id"] in only.upper()]

    results = {"upload_ms": upload_ms, "asset_id": asset_id, "runs": []}
    for run in runs:
        print(f"RUN {run['id']} {run['purpose']}…", flush=True)
        out = create_and_wait(token, run["body"])
        out["run_id"] = run["id"]
        out["purpose"] = run["purpose"]
        results["runs"].append(out)
        print(json.dumps(out, indent=2)[:800], flush=True)
        if run["id"] == "B":
            time.sleep(300)

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {OUT}", flush=True)
    return 0 if all(r.get("ok") for r in results["runs"]) else 1


if __name__ == "__main__":
    sys.exit(main())
