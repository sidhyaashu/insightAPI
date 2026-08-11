"""Core Service — SubscriptionRepository: Stripe subscription DB queries."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.subscription import Subscription


class SubscriptionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: str) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_by_stripe_id(self, stripe_subscription_id: str) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: str,
        stripe_subscription_id: str,
        stripe_price_id: str,
        tier: str,
        status: str,
        current_period_end=None,
        cancel_at_period_end: bool = False,
    ) -> Subscription:
        sub = await self.get_by_user_id(user_id)
        if sub:
            sub.stripe_subscription_id = stripe_subscription_id
            sub.stripe_price_id = stripe_price_id
            sub.tier = tier
            sub.status = status
            sub.current_period_end = current_period_end
            sub.cancel_at_period_end = cancel_at_period_end
        else:
            sub = Subscription(
                user_id=user_id,
                stripe_subscription_id=stripe_subscription_id,
                stripe_price_id=stripe_price_id,
                tier=tier,
                status=status,
                current_period_end=current_period_end,
                cancel_at_period_end=cancel_at_period_end,
            )
            self.db.add(sub)
        await self.db.commit()
        await self.db.refresh(sub)
        return sub
