from sqlalchemy.orm import Session

from app.models import CreditLedger, User


def deduct_credits_for_job(db: Session, user_id: str, amount: int, job_id: str) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return
    user.credits = max(0, user.credits - amount)
    db.add(
        CreditLedger(
            user_id=user_id,
            amount=-amount,
            type="JOB_COMPLETION",
            description=f"Credits used for job {job_id}",
            job_id=job_id,
        )
    )
    db.commit()


def check_sufficient_credits(db: Session, user_id: str | None, required: int = 1) -> bool:
    if not user_id:
        return True
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return True
    return user.credits >= required
