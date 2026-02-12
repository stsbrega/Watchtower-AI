"""
Watchtower AI - Browser WebSocket Handlers
Handles screen stream relay and chat for browser clients.
"""

import asyncio
import logging
from typing import Optional
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect

from server.agent import Agent
from server.db import get_db_session
from server.saas.auth import decode_token
from server.saas.models import User
from server.session_manager import SessionManager

logger = logging.getLogger(__name__)


def authenticate_browser_token(token: str) -> Optional[User]:
    """Validate a JWT token and return the user."""
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
        db = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user
        finally:
            db.close()
    except Exception:
        return None


async def handle_browser_stream_ws(websocket: WebSocket, session_manager: SessionManager):
    """Stream frames from the user's agent to their browser."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    user = authenticate_browser_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()
    session = session_manager.register_browser(user.id, websocket)

    # Send current agent status
    await websocket.send_json({
        "type": "agent_status",
        "connected": session.agent_ws is not None,
        "agent_status": session.agent_status,
    })

    # Send latest frame if available
    if session.latest_frame:
        try:
            await websocket.send_json(session.latest_frame)
        except Exception:
            pass

    try:
        while True:
            # Browser stream is mostly server->browser (frames relayed from ws_agent).
            # We listen for control messages from the browser.
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)

                if data.get("type") == "control":
                    # Forward control to agent
                    if session.agent_ws:
                        try:
                            await session.agent_ws.send_json(data)
                        except Exception:
                            pass

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info(f"Browser stream disconnected for user {user.id}")
    except Exception as e:
        logger.error(f"Browser stream error for user {user.id}: {e}")
    finally:
        session_manager.remove_browser(session)


async def handle_browser_chat_ws(websocket: WebSocket, session_manager: SessionManager):
    """Handle chat between browser user and Claude, with agent integration."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    user = authenticate_browser_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()
    session = session_manager.get_or_create_session(user.id)

    # Ensure session has a Claude Agent instance
    if not session.chat_agent:
        session.chat_agent = Agent()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "chat")

            if msg_type == "chat":
                message = data.get("message", "").strip()
                if not message:
                    continue

                # Check usage limits
                db = get_db_session()
                try:
                    from server.saas.auth import check_usage_limit, increment_usage
                    try:
                        check_usage_limit(user, db)
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e),
                        })
                        continue
                finally:
                    db.close()

                # Send thinking status
                await websocket.send_json({
                    "type": "status",
                    "status": "thinking",
                    "message": "Claude is analyzing your screen...",
                })

                # Get latest frame from session
                frame_b64 = None
                if data.get("include_screenshot", True) and session.latest_frame:
                    frame_b64 = session.latest_frame.get("data")

                # Call Claude
                result = await session.chat_agent.chat(message, frame_b64=frame_b64)

                # If Claude returned actions and agent is connected, dispatch them
                action_results = []
                if result["actions"] and session.agent_ws:
                    request_id = str(uuid4())
                    loop = asyncio.get_event_loop()
                    session.pending_action_future = loop.create_future()

                    try:
                        await session.agent_ws.send_json({
                            "type": "action",
                            "request_id": request_id,
                            "actions": result["actions"],
                        })
                        # Wait for results with timeout
                        action_results = await asyncio.wait_for(
                            session.pending_action_future, timeout=30.0
                        )
                    except asyncio.TimeoutError:
                        action_results = [{"error": "Agent did not respond in time"}]
                    except Exception as e:
                        action_results = [{"error": str(e)}]
                    finally:
                        session.pending_action_future = None

                # Record usage
                db = get_db_session()
                try:
                    from server.saas.auth import increment_usage
                    increment_usage(
                        user, db,
                        messages=1,
                        tokens_in=result["tokens_used"].get("input", 0),
                        tokens_out=result["tokens_used"].get("output", 0),
                        actions=len(result["actions"]),
                    )
                except Exception:
                    pass
                finally:
                    db.close()

                # Send response to browser
                await websocket.send_json({
                    "type": "response",
                    "text": result["text"],
                    "actions": result["actions"],
                    "action_results": action_results,
                    "frame_count": result["frame_count"],
                    "tokens": result["tokens_used"],
                })

            elif msg_type == "describe":
                await websocket.send_json({
                    "type": "status",
                    "status": "thinking",
                    "message": "Claude is looking at your screen...",
                })

                frame_b64 = None
                if session.latest_frame:
                    frame_b64 = session.latest_frame.get("data")

                result = await session.chat_agent.chat(
                    "What do you currently see on my screen? Describe the main elements, "
                    "any open applications, and anything notable.",
                    frame_b64=frame_b64,
                )

                await websocket.send_json({
                    "type": "response",
                    "text": result["text"],
                    "actions": [],
                    "action_results": [],
                    "frame_count": result["frame_count"],
                    "tokens": result["tokens_used"],
                })

            elif msg_type == "reset":
                session.chat_agent.reset_conversation()
                await websocket.send_json({
                    "type": "status",
                    "status": "reset",
                    "message": "Conversation reset",
                })

    except WebSocketDisconnect:
        logger.info(f"Browser chat disconnected for user {user.id}")
    except Exception as e:
        logger.error(f"Browser chat error for user {user.id}: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
