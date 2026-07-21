# Issues.md — Observability & bulk risks

Status of gaps identified in the fal timing / bulk analysis, and how Jewel AI mitigates them.

| Gap | Status | Mitigation |
| --- | --- | --- |
| 1 Blended GPU + I/O timing | **Mitigated** | `fal_webhook_received`, `storage_saved`, `fal_inference_time` + `durationSplits` on job metadata |
| 2 Bulk `stagger_ms=250` | **Mitigated** | Bulk enqueues with `stagger_ms=0`; Celery `rate_limit` via `FAL_CELERY_RATE_LIMIT` (default `10/s`) |
| 3 Missing webhook fallback | **Already fixed** | Beat `sweep_stuck_jobs` polls fal and finalizes; stamps metrics on recovery |
| 4 ETA sample poisoning | **Mitigated** | ETA samples prefer `fal_inference_time`, else worker−finalize |
| 5 Invisible upload latency | **Mitigated (server)** | `upload_ms` on asset API response + structured logs (no UI) |
| Batch wall-clock | **Mitigated** | `batches.started_at` / `completed_at` |

**UI:** Admin Monitoring and Studio were **not** changed. Phase splits are available on the API (`provider_metadata.durationSplits`, admin metrics `prep_ms` / `fal_inference_ms` / `finalize_ms` / `worker_total_ms`). Studio ETA improves automatically via de-poisoned Redis samples.

---

## Target timing model (implemented)

When fal completes (webhook or poll):

1. Stamp `timing.fal_webhook_received` (and extract `metrics.inference_time` → `fal_inference_time`)
2. Download CDN images, optional logo compose, save to storage → `timing.storage_saved` + `timing.completed`

Derived splits (`compute_duration_splits`):

| Metric | Formula |
| --- | --- |
| Prep | `prompt_ready − worker_started` |
| Pure GPU | `fal_inference_time` (seconds from fal) |
| Fal queue wait | `(fal_webhook_received − fal_queued) − fal_inference` |
| Finalize | `completed − fal_webhook_received` |
| Worker total | `completed − worker_started` |

See also [PROCESS.md](./PROCESS.md).

---

## Historical analysis (original research)

The sections below are the original deep-dive that motivated the work. Implementation status is in the table above.

### Gap 1: Blurring GPU Time with Local I/O

Previously, `completed − fal_queued` lumped fal queue wait, GPU inference, webhook transit, CDN download, logo compose, and R2 upload.

### Gap 2: Bulk Queue Staggering

`stagger_ms=250` delayed the last job in a 40-item batch by ~10s before it even left Celery. Fal’s queue absorbs bursts; rate-limiting our own workers is the correct backpressure.

### Gap 3: Webhook Fallback

`sweep_stuck_jobs` (Celery Beat every 2 minutes) already polls fal status/result and triggers finalize. Poll recovery now also stamps webhook observability fields.

### Gap 4: ETA Sample Poisoning

Rolling ETA previously used end-to-end `worker_started → completed`, including R2 variance.

### Gap 5: Invisible Asset Upload Latency

Uploads happen before job create. Server now logs and returns `upload_ms` on `/assets/upload` and `/assets/bulk-upload`.

---

## Env knobs

| Variable | Default | Purpose |
| --- | --- | --- |
| `FAL_CELERY_RATE_LIMIT` | `10/s` | Celery token-bucket for `process_image_job` |
| `WEBHOOK_PENDING_TIMEOUT_MINUTES` | `20` | Fail jobs stuck waiting on fal |
| `STUCK_JOB_MINUTES` | `15` | Requeue / recover PROCESSING jobs |
