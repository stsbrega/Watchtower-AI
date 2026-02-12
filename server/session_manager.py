"""
Watchtower AI - Session Manager
Pairs local agent connections with browser viewer connections per user.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class Session:
    user_id: int
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_ws: Optional[WebSocket] = None
    browser_ws: Optional[WebSocket] = None
    agent_status: str = "disconnected"
    latest_frame: Optional[dict] = None
    chat_agent: Optional[object] = None  # server.agent.Agent instance
    pending_action_future: Optional[asyncio.Future] = None
    created_at: float = field(default_factory=time.time)


class SessionManager:
    """In-memory session registry. Maps user_id to Session."""

    def __init__(self):
        self._sessions: dict[int, Session] = {}

    def get_or_create_session(self, user_id: int) -> Session:
        if user_id not in self._sessions:
            self._sessions[user_id] = Session(user_id=user_id)
            logger.info(f"Created session for user {user_id}")
        return self._sessions[user_id]

    def get_session(self, user_id: int) -> Optional[Session]:
        return self._sessions.get(user_id)

    def register_agent(self, user_id: int, ws: WebSocket) -> Session:
        session = self.get_or_create_session(user_id)
        session.agent_ws = ws
        session.agent_status = "connected"
        logger.info(f"Agent registered for user {user_id} (session {session.session_id})")
        return session

    def register_browser(self, user_id: int, ws: WebSocket) -> Session:
        session = self.get_or_create_session(user_id)
        session.browser_ws = ws
        logger.info(f"Browser registered for user {user_id} (session {session.session_id})")
        return session

    def remove_agent(self, session: Session):
        session.agent_ws = None
        session.agent_status = "disconnected"
        session.latest_frame = None
        logger.info(f"Agent disconnected for user {session.user_id}")

    def remove_browser(self, session: Session):
        session.browser_ws = None
        logger.info(f"Browser disconnected for user {session.user_id}")

    def cleanup_session(self, user_id: int):
        session = self._sessions.get(user_id)
        if session and not session.agent_ws and not session.browser_ws:
            del self._sessions[user_id]
            logger.info(f"Cleaned up empty session for user {user_id}")

    @property
    def active_sessions(self) -> int:
        return len(self._sessions)

    def get_stats(self) -> dict:
        agents_connected = sum(1 for s in self._sessions.values() if s.agent_ws)
        browsers_connected = sum(1 for s in self._sessions.values() if s.browser_ws)
        return {
            "total_sessions": len(self._sessions),
            "agents_connected": agents_connected,
            "browsers_connected": browsers_connected,
        }
