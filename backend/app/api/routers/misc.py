from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.auth.deps import RequireAdmin, RequireUser
from app.database import get_db
from app.models import Asset, Batch, Favorite, GenerationJob, RateEntry, ShareLink, User
from app.schemas.common import RateEntryCreate, ShareLinkCreate

router = APIRouter(tags=["admin"])


@router.get("/admin/metrics")
def admin_metrics(user: RequireAdmin, db: Session = Depends(get_db)):
    total_jobs = db.query(GenerationJob).count()
    completed = db.query(GenerationJob).filter(GenerationJob.status == "COMPLETED").count()
    failed = db.query(GenerationJob).filter(GenerationJob.status == "FAILED").count()
    return {
        "jobs": total_jobs,
        "assets": db.query(Asset).count(),
        "batches": db.query(Batch).count(),
        "favorites": db.query(Favorite).count(),
        "success_rate": round(completed / total_jobs * 100, 1) if total_jobs else 0,
        "completed": completed,
        "failed": failed,
        "recent_failures": [
            {"id": j.id, "workflow": j.workflow, "error": j.error_message, "created_at": j.created_at.isoformat()}
            for j in db.query(GenerationJob).filter(GenerationJob.status == "FAILED").order_by(GenerationJob.created_at.desc()).limit(10)
        ],
    }


@router.get("/admin/logs")
def admin_logs(user: RequireAdmin, level: str | None = None, since: str | None = None):
    return {"logs": [], "message": "Structured logs available via application stdout (JSON)"}


@router.get("/admin/usage")
def admin_usage(
    user: RequireAdmin,
    db: Session = Depends(get_db),
    days: int = 30,
    limit: int = 50,
):
    """Usage analytics from generation jobs — models, workflows, users, daily spend, live states."""
    days = max(1, min(days, 365))
    limit = max(1, min(limit, 200))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    jobs_q = db.query(GenerationJob)
    window_q = jobs_q.filter(GenerationJob.created_at >= since)

    def _status_counts(q):
        rows = q.with_entities(GenerationJob.status, func.count(GenerationJob.id)).group_by(GenerationJob.status).all()
        return {status or "UNKNOWN": count for status, count in rows}

    status_all = _status_counts(jobs_q)
    status_window = _status_counts(window_q)

    completed_all = status_all.get("COMPLETED", 0)
    failed_all = status_all.get("FAILED", 0)
    total_all = sum(status_all.values())
    pending = status_all.get("PENDING", 0)
    processing = status_all.get("PROCESSING", 0)

    cost_all = db.query(func.coalesce(func.sum(GenerationJob.cost), 0.0)).scalar() or 0.0
    cost_window = (
        db.query(func.coalesce(func.sum(GenerationJob.cost), 0.0))
        .filter(GenerationJob.created_at >= since)
        .scalar()
        or 0.0
    )
    cost_completed = (
        db.query(func.coalesce(func.sum(GenerationJob.cost), 0.0))
        .filter(GenerationJob.status == "COMPLETED")
        .scalar()
        or 0.0
    )

    by_model_rows = (
        db.query(
            GenerationJob.provider_model,
            GenerationJob.provider_used,
            GenerationJob.status,
            func.count(GenerationJob.id),
            func.coalesce(func.sum(GenerationJob.cost), 0.0),
        )
        .filter(GenerationJob.created_at >= since)
        .group_by(GenerationJob.provider_model, GenerationJob.provider_used, GenerationJob.status)
        .all()
    )
    models: dict[str, dict] = {}
    for model, provider, status, count, cost in by_model_rows:
        key = model or "(unknown)"
        entry = models.setdefault(
            key,
            {
                "model": key,
                "provider": provider or "—",
                "total": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0,
                "processing": 0,
                "estimated_cost_usd": 0.0,
            },
        )
        entry["total"] += count
        entry["estimated_cost_usd"] += float(cost or 0)
        bucket = (status or "").lower()
        if bucket in ("completed", "failed", "pending", "processing"):
            entry[bucket] += count
        if provider:
            entry["provider"] = provider
    by_model = sorted(models.values(), key=lambda m: m["total"], reverse=True)

    by_workflow_rows = (
        db.query(
            GenerationJob.workflow,
            GenerationJob.status,
            func.count(GenerationJob.id),
            func.coalesce(func.sum(GenerationJob.cost), 0.0),
        )
        .filter(GenerationJob.created_at >= since)
        .group_by(GenerationJob.workflow, GenerationJob.status)
        .all()
    )
    workflows: dict[str, dict] = {}
    for workflow, status, count, cost in by_workflow_rows:
        key = workflow or "(unknown)"
        entry = workflows.setdefault(
            key,
            {"workflow": key, "total": 0, "completed": 0, "failed": 0, "estimated_cost_usd": 0.0},
        )
        entry["total"] += count
        entry["estimated_cost_usd"] += float(cost or 0)
        if status == "COMPLETED":
            entry["completed"] += count
        elif status == "FAILED":
            entry["failed"] += count
    by_workflow = sorted(workflows.values(), key=lambda w: w["total"], reverse=True)

    by_user_rows = (
        db.query(
            User.email,
            User.id,
            func.count(GenerationJob.id),
            func.coalesce(func.sum(GenerationJob.cost), 0.0),
            func.sum(case((GenerationJob.status == "COMPLETED", 1), else_=0)),
            func.sum(case((GenerationJob.status == "FAILED", 1), else_=0)),
        )
        .outerjoin(User, User.id == GenerationJob.user_id)
        .filter(GenerationJob.created_at >= since)
        .group_by(User.email, User.id)
        .all()
    )
    by_user = [
        {
            "user_id": uid,
            "email": email or "(deleted/unknown)",
            "total": int(total or 0),
            "completed": int(completed or 0),
            "failed": int(failed or 0),
            "estimated_cost_usd": float(cost or 0),
        }
        for email, uid, total, cost, completed, failed in by_user_rows
    ]
    by_user.sort(key=lambda u: u["total"], reverse=True)

    # Daily series (UTC date)
    dialect = db.bind.dialect.name if db.bind else "sqlite"
    if dialect == "postgresql":
        day_col = func.date_trunc("day", GenerationJob.created_at)
    else:
        day_col = func.date(GenerationJob.created_at)
    daily_rows = (
        db.query(
            day_col.label("day"),
            func.count(GenerationJob.id),
            func.coalesce(func.sum(GenerationJob.cost), 0.0),
            func.sum(case((GenerationJob.status == "COMPLETED", 1), else_=0)),
            func.sum(case((GenerationJob.status == "FAILED", 1), else_=0)),
        )
        .filter(GenerationJob.created_at >= since)
        .group_by(day_col)
        .order_by(day_col)
        .all()
    )
    by_day = []
    for day, total, cost, completed, failed in daily_rows:
        if hasattr(day, "date"):
            day_str = day.date().isoformat()
        else:
            day_str = str(day)[:10]
        by_day.append(
            {
                "date": day_str,
                "total": int(total or 0),
                "completed": int(completed or 0),
                "failed": int(failed or 0),
                "estimated_cost_usd": float(cost or 0),
            }
        )

    recent = (
        db.query(GenerationJob, User.email)
        .outerjoin(User, User.id == GenerationJob.user_id)
        .order_by(GenerationJob.created_at.desc())
        .limit(limit)
        .all()
    )
    recent_jobs = []
    for job, email in recent:
        duration_ms = None
        if job.processing_started_at and job.status in ("COMPLETED", "FAILED") and job.updated_at:
            duration_ms = int((job.updated_at - job.processing_started_at).total_seconds() * 1000)
        recent_jobs.append(
            {
                "id": job.id,
                "status": job.status,
                "workflow": job.workflow,
                "jewelry_type": job.jewelry_type,
                "provider": job.provider_used,
                "model": job.provider_model,
                "estimated_cost_usd": job.cost,
                "user_email": email,
                "error_message": job.error_message,
                "retry_count": job.retry_count or 0,
                "has_output": bool(job.output_url),
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "processing_started_at": job.processing_started_at.isoformat() if job.processing_started_at else None,
                "duration_ms": duration_ms,
            }
        )

    in_flight = (
        db.query(GenerationJob, User.email)
        .outerjoin(User, User.id == GenerationJob.user_id)
        .filter(GenerationJob.status.in_(("PENDING", "PROCESSING")))
        .order_by(GenerationJob.created_at.desc())
        .limit(30)
        .all()
    )
    live = [
        {
            "id": job.id,
            "status": job.status,
            "workflow": job.workflow,
            "model": job.provider_model,
            "user_email": email,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "processing_started_at": job.processing_started_at.isoformat() if job.processing_started_at else None,
        }
        for job, email in in_flight
    ]

    return {
        "window_days": days,
        "summary": {
            "total_jobs": total_all,
            "completed": completed_all,
            "failed": failed_all,
            "pending": pending,
            "processing": processing,
            "success_rate": round(completed_all / total_all * 100, 1) if total_all else 0,
            "estimated_cost_usd_all_time": round(float(cost_all), 4),
            "estimated_cost_usd_completed": round(float(cost_completed), 4),
            "estimated_cost_usd_window": round(float(cost_window), 4),
            "jobs_in_window": sum(status_window.values()),
            "status_counts": status_all,
            "status_counts_window": status_window,
        },
        "by_model": by_model,
        "by_workflow": by_workflow,
        "by_user": by_user,
        "by_day": by_day,
        "live_jobs": live,
        "recent_jobs": recent_jobs,
        "notes": [
            "estimated_cost_usd comes from catalog cost_per_call stored on each job — fal.ai is the billing source of truth.",
            "Jewel AI does not enforce credit limits; this panel is for usage monitoring only.",
        ],
    }


@router.get("/rates")
def list_rates(db: Session = Depends(get_db)):
    return db.query(RateEntry).order_by(RateEntry.created_at.desc()).all()


@router.post("/rates")
def create_rate(body: RateEntryCreate, user: RequireAdmin, db: Session = Depends(get_db)):
    entry = RateEntry(**body.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/rates/{rate_id}")
def delete_rate(rate_id: str, user: RequireAdmin, db: Session = Depends(get_db)):
    entry = db.query(RateEntry).filter(RateEntry.id == rate_id).first()
    if not entry:
        raise HTTPException(status_code=404)
    db.delete(entry)
    db.commit()
    return {"success": True}


@router.get("/rates/live")
async def live_rates():
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/GC=F,XAG=F",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            data = resp.json()
        results = {}
        for item in data.get("chart", {}).get("result", []):
            symbol = item.get("meta", {}).get("symbol", "")
            price = item.get("meta", {}).get("regularMarketPrice")
            if symbol == "GC=F":
                results["gold_usd_oz"] = price
            elif symbol == "XAG=F":
                results["silver_usd_oz"] = price
        pkr_rate = 278.0
        return {
            "gold_pkr_per_gram": round((results.get("gold_usd_oz", 0) / 31.1035) * pkr_rate, 2),
            "silver_pkr_per_gram": round((results.get("silver_usd_oz", 0) / 31.1035) * pkr_rate, 2),
            "raw": results,
            "currency": "PKR",
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/favorites")
def list_favorites(user: RequireUser, db: Session = Depends(get_db)):
    favs = (
        db.query(Favorite)
        .filter(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )
    return [f.job_id for f in favs]


@router.post("/favorites/{job_id}")
def add_favorite(job_id: str, user: RequireUser, db: Session = Depends(get_db)):
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id, GenerationJob.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.job_id == job_id).first():
        return {"success": True}
    db.add(Favorite(user_id=user.id, job_id=job_id))
    db.commit()
    return {"success": True}


@router.delete("/favorites/{job_id}")
def remove_favorite(job_id: str, user: RequireUser, db: Session = Depends(get_db)):
    fav = db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.job_id == job_id).first()
    if fav:
        db.delete(fav)
        db.commit()
    return {"success": True}


@router.get("/projects")
def list_projects(user: RequireUser, db: Session = Depends(get_db)):
    from app.models import Project

    return (
        db.query(Project)
        .filter(Project.user_id == user.id)
        .order_by(Project.created_at.desc())
        .all()
    )


@router.get("/projects/{project_id}")
def get_project(project_id: str, user: RequireUser, db: Session = Depends(get_db)):
    from app.models import Project

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404)
    jobs = (
        db.query(GenerationJob)
        .filter(GenerationJob.project_id == project_id, GenerationJob.user_id == user.id)
        .all()
    )
    return {"project": project, "jobs": jobs}


@router.post("/share-links")
def create_share_link(body: ShareLinkCreate, user: RequireUser, db: Session = Depends(get_db)):
    job = (
        db.query(GenerationJob)
        .filter(
            GenerationJob.id == body.job_id,
            GenerationJob.user_id == user.id,
            GenerationJob.status == "COMPLETED",
        )
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Completed job not found")
    link = ShareLink(
        job_id=body.job_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=body.expires_in_hours),
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"token": link.token, "expires_at": link.expires_at}


@router.get("/pipelines/{workflow}/assemble")
def assemble_pipeline(
    workflow: str,
    user: RequireUser,
    jewelry_type: str = "Ring",
    prompt_text: str | None = None,
    db: Session = Depends(get_db),
):
    from app.pipeline.composer import ComposeInput, compose_prompt

    composed = compose_prompt(
        db,
        ComposeInput(workflow=workflow, jewelry_type=jewelry_type, prompt_text=prompt_text),
    )
    return {
        "prompt": composed.text,
        "negative_prompt": composed.negative_prompt,
        "debug": composed.debug,
    }


@router.get("/config/workflow-fields")
def workflow_fields():
    from app.pipeline.composer import VARIANT_FIELD_MAP

    return {"variantFieldMap": VARIANT_FIELD_MAP}


@router.get("/config/options")
def config_options(user: RequireUser):
    from seeds.prompts_data import JEWELRY_TYPES, WORKFLOWS

    return {
        "workflows": WORKFLOWS,
        "jewelryTypes": JEWELRY_TYPES,
        "modelsEndpoint": "/api/models",
        "aspectRatios": ["1:1", "16:9", "9:16", "3:4", "4:3"],
    }
