"""
Watchtower AI - Database Models
SQLAlchemy models for users, subscriptions, and usage tracking.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import secrets

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()


class PlanTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


PLAN_LIMITS = {
    PlanTier.FREE: {
        "messages_per_month": 50,
        "action_execution": False,
        "max_sessions": 1,
        "priority_support": False,
    },
    PlanTier.PRO: {
        "messages_per_month": 1000,
        "action_execution": True,
        "max_sessions": 3,
        "priority_support": False,
    },
    PlanTier.TEAM: {
        "messages_per_month": 5000,
        "action_execution": True,
        "max_sessions": 10,
        "max_seats": 5,
        "priority_support": True,
    },
    PlanTier.ENTERPRISE: {
        "messages_per_month": -1,
        "action_execution": True,
        "max_sessions": -1,
        "max_seats": -1,
        "priority_support": True,
        "sso": True,
    },
}


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    email_verified = Column(Boolean, default=False)

    stripe_customer_id = Column(String(255), unique=True)

    subscription = relationship("Subscription", back_populates="user", uselist=False)
    api_keys = relationship("APIKey", back_populates="user")
    usage_records = relationship("UsageRecord", back_populates="user")

    @property
    def plan(self) -> PlanTier:
        if self.subscription and self.subscription.is_active:
            return self.subscription.plan
        return PlanTier.FREE

    @property
    def limits(self) -> dict:
        return PLAN_LIMITS[self.plan]


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    plan = Column(SQLEnum(PlanTier), default=PlanTier.FREE)

    stripe_subscription_id = Column(String(255), unique=True)
    stripe_price_id = Column(String(255))

    status = Column(String(50), default="active")
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="subscription")

    @property
    def is_active(self) -> bool:
        return self.status in ("active", "trialing") and (
            self.current_period_end is None or
            self.current_period_end > datetime.utcnow()
        )


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    key_hash = Column(String(255), unique=True, nullable=False)
    key_prefix = Column(String(10), nullable=False)
    name = Column(String(255), default="Default")

    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    revoked = Column(Boolean, default=False)

    user = relationship("User", back_populates="api_keys")

    @staticmethod
    def generate() -> tuple[str, str]:
        key = f"wt_{secrets.token_urlsafe(32)}"
        import hashlib
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key, key_hash


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    messages_count = Column(Integer, default=0)
    actions_count = Column(Integer, default=0)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="usage_records")
