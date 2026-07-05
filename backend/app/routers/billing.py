"""Billing / plans — hosted payment link (or honest fake-door) for the beta.

There is NO fake payment success anywhere. With PAYMENT_LINK_URL set, checkout
sends the user to the provider's hosted page (iyzico / Lemon Squeezy / Stripe
Payment Link) — card data never touches this server. Without it, checkout says
payments aren't live. Either way, the only way a plan changes is an audited
admin action (POST /billing/set-plan or scripts/create_user.py) after the
provider's payment notification.

# TODO(stripe): real integration checklist (do NOT ship half of this):
#   1. `pip install stripe`; STRIPE_SECRET_KEY + STRIPE_WEBHOOK_SECRET from env
#      (test mode first). Never expose either to the frontend.
#   2. POST /billing/checkout -> stripe.checkout.Session.create(...) and return
#      the session URL.
#   3. POST /billing/webhook -> verify the signature with
#      stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
#      BEFORE trusting anything; update User.plan ONLY from verified
#      checkout.session.completed / customer.subscription.* events.
#   4. Never trust client-side payment state; keep /billing/set-plan admin-only.
#   5. Audit-log every plan change (already wired below).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..deps import client_ip, require_admin, require_user
from ..models import PLANS, User
from ..services import audit, events, plans
from ..services.auth import normalize_email

router = APIRouter(prefix="/billing", tags=["billing"])

# Static pricing descriptors for the pricing page. Copy is honest: beta,
# payments not live, Pro granted manually.
PLAN_CATALOG = [
    {
        "id": "free",
        "name": "Free",
        "price_monthly_usd": 0,
        "features": [
            "Browse the Türkiye + remote/EU opportunity feed",
            "Résumé-based role ranking",
            f"{plans.FREE_DAILY_LIMITS['outreach_draft']} outreach drafts / day",
            f"{plans.FREE_DAILY_LIMITS['next_move']} Next Move analyses / day",
            f"{plans.FREE_TOTAL_LIMITS['pipeline_save']} tracked pipeline items",
        ],
    },
    {
        "id": "pro",
        "name": "Pro",
        "price_monthly_usd": 12,
        "features": [
            "Everything in Free",
            "Unlimited outreach drafts (TR/EN)",
            "Unlimited Next Move analyses",
            "Unlimited pipeline items",
            "Priority support during the beta",
        ],
    },
]


class SetPlanIn(BaseModel):
    email: str = Field(max_length=320)
    plan: str = Field(max_length=20)


@router.get("/plans")
def list_plans():
    """Public pricing catalog (no account required to see pricing)."""
    return {"plans": PLAN_CATALOG, "beta": True, "payments_live": config.payments_live()}


@router.get("/plan")
def my_plan(user: User = Depends(require_user), db: Session = Depends(get_db)):
    """The caller's plan, limits, and current usage."""
    return plans.plan_overview(db, user)


@router.post("/checkout")
def checkout(user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Hosted payment link when configured; honest fake-door otherwise. Never
    fakes a successful payment — the plan flips only via the audited admin
    action after the provider confirms the payment."""
    link = config.get_payment_link_url()
    if link:
        events.track(db, "checkout_link_opened", user_id=user.id)
        return {
            "status": "payment_link",
            "url": link,
            "message": (
                "You'll pay on our provider's secure checkout page. Use the same "
                "email as your Network AI account — Pro is activated on it within "
                "a few hours of payment."
            ),
            "plan": user.plan,
        }
    events.track(db, "mock_checkout_viewed", user_id=user.id)
    return {
        "status": "unavailable",
        "message": (
            "Payments aren't live during the beta. Pro is granted manually — "
            "reply to your invite email or contact the founder and we'll upgrade "
            "your account."
        ),
        "plan": user.plan,
    }


@router.post("/set-plan")
def set_plan(
    payload: SetPlanIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only plan change (the ONLY way a plan changes in the beta). Audited."""
    if payload.plan not in PLANS:
        raise HTTPException(
            status_code=422, detail=f"plan must be one of: {', '.join(PLANS)}"
        )
    target = (
        db.query(User).filter(User.email == normalize_email(payload.email)).first()
    )
    if target is None:
        raise HTTPException(status_code=404, detail="No account with that email")

    old_plan = target.plan
    target.plan = payload.plan
    db.commit()
    audit.log(
        db, "plan_changed", user_id=admin.id, ip=client_ip(request),
        note=f"{target.email}: {old_plan} -> {payload.plan}",
    )
    return {"email": target.email, "plan": target.plan}
