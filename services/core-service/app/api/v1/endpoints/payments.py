"""Core Service — Payments router (Stripe checkout, webhooks, billing)."""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
from app.core.config import settings
from app.core.database import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.subscription_repo import SubscriptionRepository
from app.repositories.session_repo import SessionRepository
import contextlib

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["Payments"])

PRICE_TO_TIER = {
    settings.STRIPE_PRICE_STARTER: "STARTER",
    settings.STRIPE_PRICE_PRO: "PRO",
    settings.STRIPE_PRICE_ENTERPRISE: "ENTERPRISE",
}


@router.get("/plans")
async def get_payment_plans():
    """Return configured Stripe price IDs for available plans."""
    return {
        "STARTER": settings.STRIPE_PRICE_STARTER,
        "PRO": settings.STRIPE_PRICE_PRO,
        "ENTERPRISE": settings.STRIPE_PRICE_ENTERPRISE,
    }


class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str = f"{settings.APP_URL}/billing?session=success"
    cancel_url: str = f"{settings.APP_URL}/billing?session=cancel"


@router.post("/checkout")
async def create_checkout_session(body: CheckoutRequest, x_user_id: str = Header(...)):
    """Create a Stripe Checkout Session for the authenticated user."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Payment service not configured.")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(x_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Create or reuse Stripe customer
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(email=user.email, name=user.name or user.email)
            customer_id = customer.id
            await user_repo.update_stripe_customer_id(x_user_id, customer_id)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": body.price_id, "quantity": 1}],
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"user_id": x_user_id},
    )
    return {"checkout_url": session.url}


@router.get("/subscription")
async def get_subscription(x_user_id: str = Header(...)):
    """Return the current subscription for the authenticated user."""
    async with contextlib.asynccontextmanager(get_db)() as db:
        sub_repo = SubscriptionRepository(db)
        sub = await sub_repo.get_by_user_id(x_user_id)
        if not sub:
            return {"tier": "FREE", "status": "free", "subscription": None}
        return {
            "tier": sub.tier,
            "status": sub.status,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancel_at_period_end": sub.cancel_at_period_end,
        }


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events (subscription lifecycle)."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook not configured.")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature.")

    if event["type"] in ("customer.subscription.created", "customer.subscription.updated"):
        sub_data = event["data"]["object"]
        user_id = sub_data.get("metadata", {}).get("user_id") or sub_data.get("customer")
        price_id = sub_data["items"]["data"][0]["price"]["id"]
        tier = PRICE_TO_TIER.get(price_id, "STARTER")

        async with contextlib.asynccontextmanager(get_db)() as db:
            user_repo = UserRepository(db)
            sub_repo = SubscriptionRepository(db)
            await user_repo.update_tier(user_id, tier)
            await sub_repo.upsert(
                user_id=user_id,
                stripe_subscription_id=sub_data["id"],
                stripe_price_id=price_id,
                tier=tier,
                status=sub_data["status"],
            )
            session_repo = SessionRepository()
            await session_repo.cache_user_session(user_id, tier)
        logger.info(f"Subscription updated: user={user_id} tier={tier}")

    elif event["type"] == "customer.subscription.deleted":
        sub_data = event["data"]["object"]
        user_id = sub_data.get("metadata", {}).get("user_id")
        if user_id:
            async with contextlib.asynccontextmanager(get_db)() as db:
                user_repo = UserRepository(db)
                await user_repo.update_tier(user_id, "FREE")
                session_repo = SessionRepository()
                await session_repo.cache_user_session(user_id, "FREE")
            logger.info(f"Subscription canceled: user={user_id} → FREE")

    return {"received": True}
