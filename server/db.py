"""
Watchtower AI - Database Setup
SQLAlchemy engine, session factory, and middleware.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from starlette.requests import Request
from starlette.responses import Response

from server.config import server_config

engine = create_engine(
    server_config.database_url,
    pool_pre_ping=True,
    echo=False,
)
SessionLocal = sessionmaker(bind=engine)


def init_database():
    """Create all tables."""
    from server.saas.models import Base
    Base.metadata.create_all(engine)


def get_db_session() -> Session:
    """Get a standalone DB session (for WebSocket handlers)."""
    return SessionLocal()


async def db_middleware(request: Request, call_next):
    """Attach a DB session to request.state.db, close after response."""
    db = SessionLocal()
    request.state.db = db
    try:
        response = await call_next(request)
        return response
    finally:
        db.close()
