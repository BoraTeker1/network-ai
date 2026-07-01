"""Create a local user account (admin/pro/free) from the command line.

Usage (from backend/, venv active):

    python scripts/create_user.py you@example.com "a-strong-password" --plan admin
    python scripts/create_user.py you@example.com "a-strong-password" --plan admin --claim-demo-data

--claim-demo-data reassigns legacy single-user rows (user_id='demo-user' from
before auth existed) to the new account. Without it, legacy rows simply stay
invisible to every real account.

The password is taken as an argument for local dev convenience — don't use a
password you care about, and prefer creating real accounts through /signup.
"""

import argparse
import sys
from pathlib import Path

# Allow running as `python scripts/create_user.py` from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Base, SessionLocal, engine, run_lightweight_migrations  # noqa: E402
from app.models import (  # noqa: E402
    DEMO_USER_ID,
    Contact,
    EmailDraft,
    Goal,
    Meeting,
    Message,
    MomentumEvent,
    Profile,
)
from app.services import auth  # noqa: E402

USER_OWNED_MODELS = (Profile, Message, Goal, Contact, Meeting, EmailDraft, MomentumEvent)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local Network AI user.")
    parser.add_argument("email")
    parser.add_argument("password")
    parser.add_argument("--plan", choices=["free", "pro", "admin"], default="free")
    parser.add_argument(
        "--claim-demo-data",
        action="store_true",
        help="Reassign legacy 'demo-user' rows to this new account.",
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    run_lightweight_migrations()

    db = SessionLocal()
    try:
        try:
            user = auth.create_user(db, args.email, args.password, plan=args.plan)
        except auth.AuthError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        print(f"Created {user.plan} user {user.email} (id={user.id})")

        if args.claim_demo_data:
            total = 0
            for model in USER_OWNED_MODELS:
                total += (
                    db.query(model)
                    .filter(model.user_id == DEMO_USER_ID)
                    .update({"user_id": user.id})
                )
            db.commit()
            print(f"Claimed {total} legacy demo-user rows for {user.email}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
