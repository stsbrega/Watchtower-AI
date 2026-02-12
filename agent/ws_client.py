"""
Watchtower Agent - WebSocket Client
Connects to the cloud server, streams frames, receives and executes actions.
Includes auto-reconnect with exponential backoff.
"""

import asyncio
import json
import logging
import time
from typing import Optional, Callable

import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

from config import agent_config
from capture import ScreenCapture, Frame
from input_control import InputController, Action

logger = logging.getLogger(__name__)


class AgentWSClient:
    """
    WebSocket client that connects the local agent to the cloud server.

    Responsibilities:
    - Authenticate with connection token
    - Stream screen frames to the server
    - Receive action commands and execute them locally
    - Handle control messages (pause, resume, enable/disable actions)
    - Auto-reconnect on disconnect
    """

    def __init__(
        self,
        capture: ScreenCapture,
        input_controller: InputController,
        on_status_change: Optional[Callable[[str], None]] = None,
    ):
        self.capture = capture
        self.input_controller = input_controller
        self.on_status_change = on_status_change

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._connected = False
        self._reconnect_count = 0
        self._tasks: list[asyncio.Task] = []

    @property
    def connected(self) -> bool:
        return self._connected

    async def start(self):
        """Start the WebSocket client with auto-reconnect."""
        self._running = True
        self._set_status("connecting")

        while self._running:
            try:
                await self._connect_and_run()
            except (ConnectionClosed, ConnectionRefusedError, OSError) as e:
                if not self._running:
                    break
                self._connected = False
                self._set_status("disconnected")
                delay = self._get_reconnect_delay()
                logger.warning(f"Disconnected: {e}. Reconnecting in {delay:.1f}s...")
                await asyncio.sleep(delay)
                self._reconnect_count += 1
            except InvalidStatusCode as e:
                if not self._running:
                    break
                self._connected = False
                if e.status_code == 401:
                    self._set_status("auth_failed")
                    logger.error("Authentication failed. Check your connection token.")
                    # Don't spam reconnects on auth failure
                    await asyncio.sleep(30)
                else:
                    self._set_status("error")
                    delay = self._get_reconnect_delay()
                    logger.error(f"Server returned {e.status_code}. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    self._reconnect_count += 1
            except Exception as e:
                if not self._running:
                    break
                self._connected = False
                self._set_status("error")
                logger.error(f"Unexpected error: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def stop(self):
        """Disconnect and stop the client."""
        self._running = False
        self._set_status("disconnected")

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        if self._ws:
            await self._ws.close()
            self._ws = None

        self._connected = False

    async def _connect_and_run(self):
        """Connect to server and run the message loop."""
        url = f"{agent_config.server_url}?token={agent_config.connection_token}"
        logger.info(f"Connecting to {agent_config.server_url}...")

        async with websockets.connect(
            url,
            ping_interval=20,
            ping_timeout=10,
            max_size=10 * 1024 * 1024,  # 10MB max message
        ) as ws:
            self._ws = ws
            self._connected = True
            self._reconnect_count = 0
            self._set_status("connected")
            logger.info("Connected to server")

            # Send initial status
            await self._send_status()

            # Start frame streaming task
            frame_task = asyncio.create_task(self._stream_frames())
            self._tasks.append(frame_task)

            # Start keepalive task
            keepalive_task = asyncio.create_task(self._keepalive())
            self._tasks.append(keepalive_task)

            try:
                # Main message receive loop
                async for message in ws:
                    await self._handle_message(message)
            finally:
                frame_task.cancel()
                keepalive_task.cancel()
                self._tasks.clear()

    async def _handle_message(self, raw: str):
        """Handle an incoming message from the server."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from server: {raw[:100]}")
            return

        msg_type = msg.get("type")

        if msg_type == "action":
            await self._handle_action(msg)
        elif msg_type == "control":
            await self._handle_control(msg)
        elif msg_type == "pong":
            pass  # keepalive response
        else:
            logger.debug(f"Unknown message type: {msg_type}")

    async def _handle_action(self, msg: dict):
        """Execute actions from the server and return results."""
        request_id = msg.get("request_id")
        actions_data = msg.get("actions", [])
        results = []

        for action_data in actions_data:
            action = Action.from_dict(action_data)
            if not action:
                results.append({"status": "error", "message": "Invalid action"})
                continue

            try:
                # Add delay between actions
                if agent_config.action_delay > 0 and results:
                    await asyncio.sleep(agent_config.action_delay)

                result = await self.input_controller.execute(action)

                # If action requested a screenshot, capture one
                if result == "screenshot_requested":
                    frame = await self.capture.capture_single()
                    if frame:
                        await self._send_frame(frame)
                    results.append({"status": "ok", "message": "Screenshot captured"})
                else:
                    results.append({"status": "ok", "message": result})

            except Exception as e:
                logger.error(f"Action execution failed: {e}")
                results.append({"status": "error", "message": str(e)})

        # Send results back to server
        await self._send_json({
            "type": "action_result",
            "request_id": request_id,
            "results": results,
        })

        # Capture a follow-up frame after actions
        await asyncio.sleep(0.3)
        frame = await self.capture.capture_single()
        if frame:
            await self._send_frame(frame)

    async def _handle_control(self, msg: dict):
        """Handle control commands from the server."""
        command = msg.get("command")

        if command == "pause":
            self.capture.pause()
            logger.info("Capture paused by server")
        elif command == "resume":
            self.capture.resume()
            logger.info("Capture resumed by server")
        elif command == "enable_actions":
            self.input_controller.enable()
            logger.info("Actions enabled by server")
        elif command == "disable_actions":
            self.input_controller.disable()
            logger.info("Actions disabled by server")
        else:
            logger.warning(f"Unknown control command: {command}")

        # Send updated status
        await self._send_status()

    async def _stream_frames(self):
        """Subscribe to capture frames and stream them to the server."""
        frame_queue = self.capture.subscribe()
        try:
            while self._running and self._connected:
                try:
                    frame: Frame = await asyncio.wait_for(frame_queue.get(), timeout=5.0)
                    await self._send_frame(frame)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    if self._running:
                        logger.error(f"Frame streaming error: {e}")
                    break
        finally:
            self.capture.unsubscribe(frame_queue)

    async def _send_frame(self, frame: Frame):
        """Send a frame to the server."""
        if not self._ws or not self._connected:
            return

        try:
            await self._ws.send(json.dumps({
                "type": "frame",
                "image_b64": frame.image_b64,
                "width": frame.width,
                "height": frame.height,
                "frame_number": frame.frame_number,
                "timestamp": frame.timestamp,
            }))
        except Exception as e:
            logger.error(f"Failed to send frame: {e}")
            self._connected = False

    async def _send_status(self):
        """Send current agent status to the server."""
        await self._send_json({
            "type": "status",
            "agent_status": "running" if self.capture.is_running else "stopped",
            "capture_paused": self.capture.is_paused,
            "capture_fps": agent_config.capture_fps,
            "actions_enabled": self.input_controller.enabled,
            "capture_stats": self.capture.stats,
        })

    async def _send_json(self, data: dict):
        """Send JSON data to the server."""
        if not self._ws or not self._connected:
            return

        try:
            await self._ws.send(json.dumps(data))
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self._connected = False

    async def _keepalive(self):
        """Send periodic pings to keep the connection alive."""
        while self._running and self._connected:
            try:
                await asyncio.sleep(30)
                await self._send_json({"type": "ping", "timestamp": time.time()})
            except Exception:
                break

    def _get_reconnect_delay(self) -> float:
        """Calculate reconnect delay with exponential backoff."""
        delay = agent_config.reconnect_delay * (agent_config.reconnect_backoff ** self._reconnect_count)
        return min(delay, agent_config.max_reconnect_delay)

    def _set_status(self, status: str):
        """Update connection status and notify callback."""
        logger.info(f"Status: {status}")
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception:
                pass
