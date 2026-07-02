from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.deps import RequireAdmin, RequireUser
from app.database import get_db
from app.models import Asset, Batch, CreditLedger, Favorite, GenerationJob, RateEntry, ShareLink, User
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


@router.get("/credits/balance")
def credit_balance(user: RequireUser, db: Session = Depends(get_db)):
    return {"credits": user.credits}


@router.get("/credits/history")
def credit_history(user: RequireUser, db: Session = Depends(get_db)):
    rows = db.query(CreditLedger).filter(CreditLedger.user_id == user.id).order_by(CreditLedger.created_at.desc()).limit(50)
    return list(rows)


@router.get("/pipelines/{workflow}/assemble")
def assemble_pipeline(
    workflow: str,
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
