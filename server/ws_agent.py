"""
Watchtower AI - Agent WebSocket Handler
Handles connections from local agents (screen capture + input control).
"""

import hashlib
import logging

from fastapi import WebSocket, WebSocketDisconnect

from server.db import get_db_session
from server.saas.models import APIKey, User
from server.session_manager import SessionManager

logger = logging.getLogger(__name__)


def authenticate_agent_token(token: str):
    """Validate an agent connection token (API key) and return the user."""
    db = get_db_session()
    try:
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        api_key = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.revoked == False,
        ).first()

        if not api_key:
            return None

        user = db.query(User).filter(User.id == api_key.user_id).first()
        return user
    finally:
        db.close()


async def handle_agent_ws(websocket: WebSocket, session_manager: SessionManager):
    """Handle a local agent's WebSocket connection."""

    # Extract and validate token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    user = authenticate_agent_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Accept and register
    await websocket.accept()
    session = session_manager.register_agent(user.id, websocket)
    logger.info(f"Agent connected for user {user.id} ({user.email})")

    # Notify browser if connected
    if session.browser_ws:
        try:
            await session.browser_ws.send_json({
                "type": "agent_status",
                "connected": True,
                "agent_status": "connected",
            })
        except Exception:
            pass

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "frame":
                # Store latest frame and relay to browser
                session.latest_frame = data
                if session.browser_ws:
                    try:
                        await session.browser_ws.send_json(data)
                    except Exception:
                        session.browser_ws = None

            elif msg_type == "action_result":
                # Resolve pending action future from chat handler
                if session.pending_action_future and not session.pending_action_future.done():
                    session.pending_action_future.set_result(data.get("results", []))

            elif msg_type == "status":
                session.agent_status = data.get("agent_status", "ready")
                if session.browser_ws:
                    try:
                        await session.browser_ws.send_json({
                            "type": "agent_status",
                            "connected": True,
                            "agent_status": session.agent_status,
                            "capture_fps": data.get("capture_fps"),
                            "actions_enabled": data.get("actions_enabled"),
                        })
                    except Exception:
                        pass

            elif msg_type == "pong":
                pass

    except WebSocketDisconnect:
        logger.info(f"Agent disconnected for user {user.id}")
    except Exception as e:
        logger.error(f"Agent WS error for user {user.id}: {e}")
    finally:
        session_manager.remove_agent(session)
        # Notify browser
        if session.browser_ws:
            try:
                await session.browser_ws.send_json({
                    "type": "agent_status",
                    "connected": False,
                    "agent_status": "disconnected",
                })
            except Exception:
                pass
