# FAL Generation Latency — Root Cause Report

**Date:** 2026-07-22  
**Environment:** Railway production (`jewel-ai.up.railway.app`)  
**Scope:** Evidence-only investigation (no product logic rewrites beyond observability gap-fill)

---

## Executive verdict

**The bottleneck is on the FAL.ai side of `client.subscribe()` (queue wait + GPU), not Jewel AI prep or post-processing.**

For a warm Catalog Image job on `fal-ai/nano-banana-pro/edit`:

| Phase | Time | Share of worker |
| --- | --- | --- |
| Prep (prompt + image plan) | ~0.2 s | ~1% |
| **FAL subscribe wall (`T2_fal_api_ms`)** | **~21 s** | **~95%** |
| CDN download | ~0.6–0.8 s | ~3% |
| Logo + R2 save (finalize) | ~0.2–0.3 s | ~1% |

App-side prep/finalize are **not** the latency problem. Model choice is: `openai/gpt-image-2/edit` spent **~189 s** in the same FAL subscribe wall.

Cross-check these `fal_request_id` values in FAL App Analytics (**Request Startup** vs **Request Duration**):

| Run | Model | `fal_request_id` |
| --- | --- | --- |
| A | nano-banana-pro/edit | `019f891d-ff03-77d2-8978-f184d1f1d807` |
| D | nano-banana-pro/edit | `019f891e-af5c-7683-bd59-534fb82966ae` |
| E | gpt-image-2/edit | `019f891f-14d1-7790-8f32-d27eff69a057` |

`fal_inference_time` was still **null** in the subscribe result payload, so Startup vs GPU must be read from the FAL dashboard for those IDs. Worker logs showed prolonged `HTTP 202 Accepted` status polls before completion — consistent with **queue/startup time inside the subscribe wall**.

---

## Phase 1 — Production baseline

### Config (Railway)

| Setting | Value |
| --- | --- |
| `NODE_ENV` | `production` |
| `STORAGE_BACKEND` | `r2` |
| `API_PUBLIC_URL` | `https://jewel-ai.up.railway.app` |
| `FAL_USE_WEBHOOKS` | **unset → false** (subscribe / in-process wait) |
| `LATENCY_TRACE` | set to **true** on API + worker during investigation |
| `FAL_CELERY_RATE_LIMIT` | default `10/s` |
| `CELERY_WORKER_CONCURRENCY` | default `3` |
| Services | Jewel-Ai-v3, worker, beat — Online (sfo) |

### Last 19 completed jobs (DB dump)

| Metric | p50 | min | max |
| --- | --- | --- | --- |
| `worker_total_ms` | 167,568 (~168 s) | 22 s | 227 s |
| `prep_ms` | 43 | 22 | 156 |
| Approx FAL+finalize (`worker − prep`) | 167,420 | 22 s | 227 s |
| `pre_worker_queue_ms` | 2,438 | 2 s | **200 s** |

Decision-tree labels on historical jobs:

- **13 / 19** → `H1_or_H2_fal_wall_blended_subscribe` (FAL subscribe dominates)
- **6 / 19** → `H5_celery_queue` (bulk / worker backlog; queue wait up to ~200 s)

Historical observability gap (fixed in this investigation):

- `fal_request_id`: **100% null** on subscribe path (before gap-fill)
- `fal_inference_time`: **100% null**
- No `fal_queued` / `fal_webhook_received` stamps (expected when webhooks off)

---

## Phase 2–3 — Tracing + controlled tests

Enabled `LATENCY_TRACE=true`, redeployed, ran production jobs via Studio API:

| Run | Purpose | Model | Wall (client) | `T2_fal_api_ms` | Prep | Finalize | CDN fetch |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | Warm baseline | nano-banana-pro | 27.9 s | **21.1 s** | 0.2 s | 0.3 s | 0.6 s |
| D | Prompt add-on | nano-banana-pro | 28.0 s | **21.5 s** | 0.1 s | 0.2 s | 0.8 s |
| E | Alternate model | gpt-image-2 | **192.5 s** | **189.4 s** | 0.2 s | 0.2 s | 0.9 s |

Runs B (cold start idle) and C (theme+logo) were not required once A/D/E already isolated FAL wall as >90% — optional follow-up if Startup vs Duration needs cold-start confirmation on FAL’s side.

Upload (pre-job): `upload_ms` ≈ 0.6–0.8 s — **H6 not material**.

---

## Phase 4 — Waterfall (Run A)

```text
created → worker_started     ~2.3 s   Celery claim (H5 minor)
worker_started → prompt_ready ~0.2 s   Prep (H3 ruled out)
fal_submit → fal_result_received ~21.1 s  ★ FAL subscribe wall (H1+H2)
fal_result_received → storage_saved ~0.3 s Finalize (H4 ruled out)
```

**Decision tree:** `fal_wall_ms` ≈ 95% of `worker_total_ms` → **FAL-bound**.  
App prep &lt; 1%, finalize &lt; 2%.

Prompt add-on (D) did **not** increase latency vs A → prompt size is not the driver for nano-banana.

Model switch (E) increased FAL wall **~9×** → **model/endpoint choice is the primary product lever**.

---

## Hypothesis outcomes

| ID | Hypothesis | Result |
| --- | --- | --- |
| H1 | FAL queue / cold start | **Likely contributor** inside subscribe wall (status `202 Accepted` polls); confirm Startup in FAL dashboard |
| H2 | FAL GPU | **Likely contributor** inside same wall; confirm Request Duration in FAL dashboard |
| H3 | App prep | **Rejected** (~0.1–0.3 s) |
| H4 | App post / R2 | **Rejected** (~0.2–0.3 s finalize; CDN ~0.6–0.9 s) |
| H5 | Celery queue | **Confirmed under bulk** historically (up to ~200 s); single-job queue ~2 s |
| H6 | Upload | **Rejected** (&lt;1 s) |
| H7 | Client poll | Not dominant vs 21–189 s server wait |
| H8 | Rate limit | Not needed to explain single-job latency |

---

## Gap-fill shipped

Commit `ef015ed`:

- Capture `fal_request_id` via subscribe `on_enqueue`
- Stamp `timing.fal_result_received`
- Persist `latencyTrace` (`T2_fal_api_ms`, `fal_cdn_fetch_ms`, …)
- Extend `compute_duration_splits` for subscribe path (`fal_wall_ms`)

Scripts (ops):

- [`backend/scripts/dump_latency_baseline.py`](../../backend/scripts/dump_latency_baseline.py)
- [`backend/scripts/analyze_latency_waterfall.py`](../../backend/scripts/analyze_latency_waterfall.py)
- [`backend/scripts/run_latency_test_matrix.py`](../../backend/scripts/run_latency_test_matrix.py)

---

## Evidence-based fix directions (do not implement until product prioritizes)

1. **Default Studio model** — Prefer `fal-ai/nano-banana-pro/edit` (~20–30 s) over `openai/gpt-image-2/edit` (~3 min) unless quality requires the slower model. Warn in UI when selecting slow endpoints.
2. **FAL dashboard** — For the three `fal_request_id`s above, measure Startup vs Duration. If Startup dominates → concurrency / plan / cold start with FAL. If Duration dominates → model/prompt/image-count GPU cost.
3. **Bulk concurrency** — Scale Celery workers or lower concurrent bulk size when `pre_worker_queue_ms` spikes (H5).
4. **Optional webhooks** — `FAL_USE_WEBHOOKS=true` can free worker slots while waiting; does not reduce FAL GPU time.
5. **Do not** spend engineering time optimizing prompt compose or R2 save for this symptom — measured in hundreds of ms.

---

## How to reproduce

```powershell
cd "Jewel AI/backend"
$env:BASE_URL = "https://jewel-ai.up.railway.app"
$env:EMAIL = "studio@jewelai.com"
$env:PASSWORD = "studio123"
$env:ASSET_URL = "<https URL of a real product image>"
$env:RUN_ONLY = "A"   # or DE / ALL
.\.venv\Scripts\python.exe scripts\run_latency_test_matrix.py
```

Ensure `LATENCY_TRACE=true` on API + worker. Grep logs for `LATENCY_TRACE` / `fal_request_id`.
