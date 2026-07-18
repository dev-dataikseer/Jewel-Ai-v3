from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth.deps import RequireAdmin, RequireUser
from app.auth.security import hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas.common import UserOut

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: Optional[str] = None
    role: str = "user"


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8)
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class MeUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8)
    current_password: Optional[str] = None
    name: Optional[str] = None


def _count_admins(db: Session) -> int:
    return db.query(User).filter(User.role == "admin", User.is_active == True).count()  # noqa: E712


def _validate_role(role: str) -> None:
    if role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")


@router.get("", response_model=list[UserOut])
def list_users(user: RequireAdmin, db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("", response_model=UserOut)
def create_user(body: UserCreate, user: RequireAdmin, db: Session = Depends(get_db)):
    _validate_role(body.role)
    email = body.email.strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    new_user = User(
        email=email,
        hashed_password=hash_password(body.password),
        name=body.name or email.split("@")[0],
        role=body.role,
        credits=500,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.patch("/me", response_model=UserOut)
def update_me(body: MeUpdate, user: RequireUser, db: Session = Depends(get_db)):
    if body.email and body.email.strip() != user.email:
        if db.query(User).filter(User.email == body.email.strip(), User.id != user.id).first():
            raise HTTPException(status_code=409, detail="Email already in use")
        user.email = body.email.strip()

    if body.name is not None:
        user.name = body.name

    if body.password:
        if not body.current_password or not verify_password(body.current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        user.hashed_password = hash_password(body.password)

    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, body: UserUpdate, admin: RequireAdmin, db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if body.role:
        _validate_role(body.role)

    if body.email and body.email.strip() != target.email:
        if db.query(User).filter(User.email == body.email.strip(), User.id != user_id).first():
            raise HTTPException(status_code=409, detail="Email already in use")
        target.email = body.email.strip()

    if body.name is not None:
        target.name = body.name

    if body.password:
        target.hashed_password = hash_password(body.password)

    if body.role is not None:
        if target.role == "admin" and body.role != "admin" and _count_admins(db) <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last admin")
        target.role = body.role

    if body.is_active is not None:
        if target.role == "admin" and not body.is_active and _count_admins(db) <= 1:
            raise HTTPException(status_code=400, detail="Cannot deactivate the last admin")
        target.is_active = body.is_active

    db.commit()
    db.refresh(target)
    return target


@router.delete("/{user_id}")
def deactivate_user(user_id: str, admin: RequireAdmin, db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == "admin" and _count_admins(db) <= 1:
        raise HTTPException(status_code=400, detail="Cannot deactivate the last admin")
    target.is_active = False
    db.commit()
    return {"success": True}
