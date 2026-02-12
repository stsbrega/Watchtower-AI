"""
Watchtower AI - SaaS API Routes
Authentication, billing, user management, and connection token endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from server.saas.models import User, APIKey, Subscription, PlanTier
from server.saas.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, check_usage_limit,
)
from server.saas.billing import create_checkout_session, create_portal_session, handle_webhook

router = APIRouter(prefix="/api/v1", tags=["auth"])


# ── Request/Response Models ──────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400

class UserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    plan: str
    messages_used: int
    messages_limit: int
    created_at: datetime

class CheckoutRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str

class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: Optional[datetime]


# ── Auth Routes ──────────────────────────────────────────────────────

@router.post("/auth/register", response_model=TokenResponse)
async def register(request: Request, body: RegisterRequest):
    db: Session = request.state.db

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
async def login(request: Request, body: LoginRequest):
    db: Session = request.state.db

    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=UserResponse)
async def get_me(request: Request, user: User = Depends(get_current_user)):
    db: Session = request.state.db
    usage = check_usage_limit(user, db)

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        plan=user.plan.value,
        messages_used=usage["messages_used"],
        messages_limit=usage["messages_limit"],
        created_at=user.created_at,
    )


# ── API Key / Connection Token Routes ────────────────────────────────

@router.post("/api-keys")
async def create_api_key(request: Request, name: str = "Default", user: User = Depends(get_current_user)):
    db: Session = request.state.db

    existing_count = db.query(APIKey).filter(
        APIKey.user_id == user.id,
        APIKey.revoked == False,
    ).count()

    if existing_count >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 API keys allowed")

    key, key_hash = APIKey.generate()

    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key[:10],
        name=name,
    )
    db.add(api_key)
    db.commit()

    return {"id": api_key.id, "key": key, "name": name, "created_at": api_key.created_at}


@router.post("/api-keys/connection-token")
async def create_connection_token(request: Request, user: User = Depends(get_current_user)):
    """Generate a connection token for the local agent."""
    db: Session = request.state.db

    key, key_hash = APIKey.generate()

    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key[:10],
        name="Agent Connection Token",
    )
    db.add(api_key)
    db.commit()

    host = request.headers.get("host", "localhost:8765")
    protocol = "wss" if request.url.scheme == "https" else "ws"

    return {
        "connection_token": key,
        "server_url": f"{protocol}://{host}/ws/agent",
    }


@router.get("/api-keys")
async def list_api_keys(request: Request, user: User = Depends(get_current_user)):
    db: Session = request.state.db

    keys = db.query(APIKey).filter(
        APIKey.user_id == user.id,
        APIKey.revoked == False,
    ).all()

    return [
        APIKeyResponse(
            id=k.id, name=k.name, key_prefix=k.key_prefix,
            created_at=k.created_at, last_used_at=k.last_used_at,
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(request: Request, key_id: int, user: User = Depends(get_current_user)):
    db: Session = request.state.db

    api_key = db.query(APIKey).filter(
        APIKey.id == key_id, APIKey.user_id == user.id,
    ).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.revoked = True
    db.commit()
    return {"status": "revoked"}


# ── Billing Routes ───────────────────────────────────────────────────

@router.post("/billing/checkout")
async def create_checkout(request: Request, body: CheckoutRequest, user: User = Depends(get_current_user)):
    db: Session = request.state.db

    try:
        plan = PlanTier(body.plan)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan")

    checkout_url = create_checkout_session(
        user=user, plan=plan, db=db,
        success_url=body.success_url, cancel_url=body.cancel_url,
    )
    return {"checkout_url": checkout_url}


@router.post("/billing/portal")
async def billing_portal(request: Request, return_url: str, user: User = Depends(get_current_user)):
    db: Session = request.state.db
    portal_url = create_portal_session(user, db, return_url)
    return {"portal_url": portal_url}


@router.get("/billing/subscription")
async def get_subscription(request: Request, user: User = Depends(get_current_user)):
    sub = user.subscription

    if not sub or not sub.is_active or sub.plan == PlanTier.FREE:
        return {"plan": "free", "status": "active", "limits": user.limits}

    return {
        "plan": sub.plan.value,
        "status": sub.status,
        "current_period_end": sub.current_period_end,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "limits": user.limits,
    }


# ── Webhook Route ────────────────────────────────────────────────────

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    db: Session = request.state.db
    return handle_webhook(payload, sig_header, db)


# ── Usage Stats ──────────────────────────────────────────────────────

@router.get("/usage")
async def get_usage(request: Request, user: User = Depends(get_current_user)):
    db: Session = request.state.db

    from server.saas.models import UsageRecord

    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    usage = db.query(UsageRecord).filter(
        UsageRecord.user_id == user.id,
        UsageRecord.period_start == period_start,
    ).first()

    limits = user.limits

    return {
        "period_start": period_start,
        "period_end": (period_start + timedelta(days=32)).replace(day=1),
        "messages": {"used": usage.messages_count if usage else 0, "limit": limits["messages_per_month"]},
        "actions": {"used": usage.actions_count if usage else 0, "enabled": limits["action_execution"]},
        "tokens": {"input": usage.tokens_input if usage else 0, "output": usage.tokens_output if usage else 0},
        "plan": user.plan.value,
    }
