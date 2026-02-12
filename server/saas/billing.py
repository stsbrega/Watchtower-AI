"""
Watchtower AI - Stripe Billing Integration
Handles subscriptions, checkout, and webhooks.
"""

from datetime import datetime
from typing import Optional

import stripe
from fastapi import HTTPException
from sqlalchemy.orm import Session

from server.config import server_config
from server.saas.models import User, Subscription, PlanTier

stripe.api_key = server_config.stripe_secret_key

STRIPE_PRICES = {
    PlanTier.PRO: server_config.stripe_price_pro,
    PlanTier.TEAM: server_config.stripe_price_team,
}


def get_or_create_customer(user: User, db: Session) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.name,
        metadata={"user_id": str(user.id)},
    )

    user.stripe_customer_id = customer.id
    db.commit()

    return customer.id


def create_checkout_session(user: User, plan: PlanTier, db: Session, success_url: str, cancel_url: str) -> str:
    if plan == PlanTier.FREE:
        raise HTTPException(status_code=400, detail="Cannot checkout for free plan")

    if plan == PlanTier.ENTERPRISE:
        raise HTTPException(status_code=400, detail="Contact sales for Enterprise plan")

    customer_id = get_or_create_customer(user, db)
    price_id = STRIPE_PRICES.get(plan)

    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid plan")

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(user.id), "plan": plan.value},
    )

    return session.url


def create_portal_session(user: User, db: Session, return_url: str) -> str:
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url,
    )

    return session.url


def handle_webhook(payload: bytes, sig_header: str, db: Session) -> dict:
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, server_config.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data, db)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data, db)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(data, db)

    return {"status": "ok", "event": event_type}


def _handle_checkout_completed(data: dict, db: Session):
    user_id = int(data["metadata"]["user_id"])
    plan = PlanTier(data["metadata"]["plan"])

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return

    subscription_id = data.get("subscription")
    if not subscription_id:
        return

    stripe_sub = stripe.Subscription.retrieve(subscription_id)

    sub = user.subscription
    if not sub:
        sub = Subscription(user_id=user.id)
        db.add(sub)

    sub.plan = plan
    sub.stripe_subscription_id = subscription_id
    sub.stripe_price_id = stripe_sub["items"]["data"][0]["price"]["id"]
    sub.status = stripe_sub["status"]
    sub.current_period_start = datetime.fromtimestamp(stripe_sub["current_period_start"])
    sub.current_period_end = datetime.fromtimestamp(stripe_sub["current_period_end"])
    db.commit()


def _handle_subscription_updated(data: dict, db: Session):
    sub = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == data["id"]
    ).first()
    if not sub:
        return
    sub.status = data["status"]
    sub.current_period_start = datetime.fromtimestamp(data["current_period_start"])
    sub.current_period_end = datetime.fromtimestamp(data["current_period_end"])
    sub.cancel_at_period_end = data.get("cancel_at_period_end", False)
    db.commit()


def _handle_subscription_deleted(data: dict, db: Session):
    sub = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == data["id"]
    ).first()
    if sub:
        sub.status = "canceled"
        sub.plan = PlanTier.FREE
        db.commit()


def _handle_payment_failed(data: dict, db: Session):
    customer_id = data.get("customer")
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if user and user.subscription:
        user.subscription.status = "past_due"
        db.commit()
