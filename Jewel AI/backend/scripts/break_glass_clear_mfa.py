#!/usr/bin/env python3
"""Break-glass: clear admin TOTP after out-of-band identity verification.

Usage (from backend/ with DATABASE_URL set):
  python -m scripts.break_glass_clear_mfa admin@jewelai.com --confirm YES

Writes an audit_logs row with actor_user_id=null and action=mfa.break_glass_clear.
"""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Clear admin MFA (break-glass)")
    parser.add_argument("email")
    parser.add_argument("--confirm", required=True, help='Must be YES')
    args = parser.parse_args()
    if args.confirm != "YES":
        print("Refusing: pass --confirm YES", file=sys.stderr)
        return 2

    from app.database import SessionLocal
    from app.models import User
    from app.services.audit import write_audit
    from app.services.mfa import clear_user_totp

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email.strip()).first()
        if not user:
            print("User not found", file=sys.stderr)
            return 1
        if (user.role or "").lower() != "admin":
            print("Refusing: target is not admin", file=sys.stderr)
            return 1
        clear_user_totp(db, user)
        write_audit(
            db,
            actor_user_id=None,
            action="mfa.break_glass_clear",
            entity_type="user",
            entity_id=user.id,
            after={"email": user.email},
        )
        db.commit()
        print(f"Cleared MFA for {user.email}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
