"""
Watchtower AI - Authentication
JWT-based authentication with password hashing.
"""

from datetime import datetime, timedelta
from typing import Optional
import hashlib

from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from server.config import server_config
from server.saas.models import User, APIKey, PlanTier, PLAN_LIMITS

SECRET_KEY = server_config.jwt_secret_key
ALGORITHM = server_config.jwt_algorithm
ACCESS_TOKEN_EXPIRE_HOURS = server_config.jwt_expire_hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    api_key: str = Security(api_key_header),
) -> User:
    db: Session = request.state.db

    # Try API Key first
    if api_key:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        api_key_record = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.revoked == False,
        ).first()

        if api_key_record:
            if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
                raise HTTPException(status_code=401, detail="API key expired")
            api_key_record.last_used_at = datetime.utcnow()
            db.commit()
            return api_key_record.user

    # Try JWT Bearer token
    if credentials:
        payload = decode_token(credentials.credentials)
        user_id = int(payload["sub"])
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user

    raise HTTPException(status_code=401, detail="Not authenticated")


def check_usage_limit(user: User, db: Session) -> dict:
    limits = user.limits
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    from server.saas.models import UsageRecord
    usage = db.query(UsageRecord).filter(
        UsageRecord.user_id == user.id,
        UsageRecord.period_start == period_start,
    ).first()

    current_messages = usage.messages_count if usage else 0
    max_messages = limits["messages_per_month"]

    if max_messages != -1 and current_messages >= max_messages:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Monthly message limit reached",
                "current": current_messages,
                "limit": max_messages,
                "plan": user.plan.value,
                "upgrade_url": "/pricing",
            }
        )

    return {
        "messages_used": current_messages,
        "messages_limit": max_messages,
        "actions_enabled": limits["action_execution"],
        "plan": user.plan.value,
    }


def increment_usage(user: User, db: Session, messages: int = 1, actions: int = 0, tokens_in: int = 0, tokens_out: int = 0):
    from server.saas.models import UsageRecord

    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_end = (period_start + timedelta(days=32)).replace(day=1)

    usage = db.query(UsageRecord).filter(
        UsageRecord.user_id == user.id,
        UsageRecord.period_start == period_start,
    ).first()

    if not usage:
        usage = UsageRecord(
            user_id=user.id,
            period_start=period_start,
            period_end=period_end,
        )
        db.add(usage)

    usage.messages_count += messages
    usage.actions_count += actions
    usage.tokens_input += tokens_in
    usage.tokens_output += tokens_out
    db.commit()
