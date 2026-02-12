"""
Input Controller
Translates action commands into actual mouse/keyboard/system events.
Uses pyautogui for cross-platform input simulation.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

from config import agent_config as config

logger = logging.getLogger(__name__)

# Lazy import — pyautogui requires a display, so we defer import
_pyautogui = None


def _get_pyautogui():
    """Lazy-load pyautogui to avoid import errors in headless environments."""
    global _pyautogui
    if _pyautogui is None:
        import pyautogui
        pyautogui.FAILSAFE = True     # Move mouse to corner to abort
        pyautogui.PAUSE = 0.1         # Small pause between actions
        _pyautogui = pyautogui
    return _pyautogui


@dataclass
class Action:
    """Represents a single action to perform on the local machine."""
    type: str                              # click, type, key, scroll, move, screenshot, wait
    x: Optional[int] = None
    y: Optional[int] = None
    button: str = "left"                   # left, right, middle
    text: Optional[str] = None
    keys: Optional[str] = None             # e.g., "ctrl+s", "enter"
    direction: str = "down"                # scroll direction
    amount: int = 3                        # scroll amount
    seconds: float = 1.0                   # wait duration

    def to_dict(self) -> dict:
        d = {"type": self.type}
        if self.x is not None:
            d["x"] = self.x
        if self.y is not None:
            d["y"] = self.y
        if self.type == "click":
            d["button"] = self.button
        if self.text:
            d["text"] = self.text
        if self.keys:
            d["keys"] = self.keys
        if self.type == "scroll":
            d["direction"] = self.direction
            d["amount"] = self.amount
        if self.type == "wait":
            d["seconds"] = self.seconds
        return d

    @staticmethod
    def from_dict(d: dict) -> Optional["Action"]:
        """Parse an action from a dict. Returns None if invalid."""
        action_type = d.get("type")
        if not action_type:
            return None

        valid_types = {"click", "type", "key", "scroll", "move", "screenshot", "wait"}
        if action_type not in valid_types:
            logger.warning(f"Unknown action type: {action_type}")
            return None

        return Action(
            type=action_type,
            x=d.get("x"),
            y=d.get("y"),
            button=d.get("button", "left"),
            text=d.get("text"),
            keys=d.get("keys"),
            direction=d.get("direction", "down"),
            amount=d.get("amount", 3),
            seconds=min(d.get("seconds", 1.0), 10.0),  # cap at 10 seconds
        )


class InputController:
    """
    Executes actions on the local machine.
    All actions require action_execution to be enabled.
    """

    def __init__(self):
        self._enabled = config.action_execution
        self._action_log: list[dict] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self):
        self._enabled = True
        logger.warning("Action execution ENABLED — Claude can now control mouse/keyboard")

    def disable(self):
        self._enabled = False
        logger.info("Action execution disabled")

    @property
    def action_log(self) -> list[dict]:
        return self._action_log[-100:]  # last 100 actions

    async def execute(self, action: Action) -> str:
        """Execute a single action. Returns a status message."""
        if not self._enabled:
            return "Action execution is disabled. Enable it in settings."

        self._action_log.append(action.to_dict())

        try:
            return await asyncio.to_thread(self._execute_sync, action)
        except Exception as e:
            logger.error(f"Action failed: {action.type} — {e}")
            raise

    def _execute_sync(self, action: Action) -> str:
        """Synchronous action execution (runs in thread pool)."""
        pag = _get_pyautogui()

        match action.type:
            case "click":
                return self._do_click(pag, action)
            case "type":
                return self._do_type(pag, action)
            case "key":
                return self._do_key(pag, action)
            case "scroll":
                return self._do_scroll(pag, action)
            case "move":
                return self._do_move(pag, action)
            case "wait":
                return self._do_wait(action)
            case "screenshot":
                return "screenshot_requested"
            case _:
                return f"Unknown action: {action.type}"

    def _do_click(self, pag, action: Action) -> str:
        """Perform a mouse click."""
        if action.x is None or action.y is None:
            return "Error: click requires x and y coordinates"

        # Scale coordinates back to actual screen resolution
        x = int(action.x / config.capture_scale)
        y = int(action.y / config.capture_scale)

        button = action.button if action.button in ("left", "right", "middle") else "left"
        pag.click(x=x, y=y, button=button)
        return f"Clicked ({x}, {y}) with {button} button"

    def _do_type(self, pag, action: Action) -> str:
        """Type text."""
        if not action.text:
            return "Error: type requires text"

        # Safety: limit text length
        text = action.text[:500]
        pag.typewrite(text, interval=0.02) if text.isascii() else pag.write(text)
        return f"Typed {len(text)} characters"

    def _do_key(self, pag, action: Action) -> str:
        """Press a key combination."""
        if not action.keys:
            return "Error: key requires keys"

        # Parse key combo like "ctrl+s" or "enter"
        keys = action.keys.lower().strip()

        # Block dangerous combos
        dangerous = {"alt+f4", "ctrl+alt+delete", "super+l"}
        if keys in dangerous:
            return f"Blocked dangerous key combo: {keys}"

        if "+" in keys:
            parts = keys.split("+")
            pag.hotkey(*parts)
        else:
            pag.press(keys)

        return f"Pressed: {keys}"

    def _do_scroll(self, pag, action: Action) -> str:
        """Scroll the mouse wheel."""
        amount = min(abs(action.amount), 20)  # cap scroll amount
        if action.direction in ("up",):
            amount = abs(amount)
        elif action.direction in ("down",):
            amount = -abs(amount)

        x = int(action.x / config.capture_scale) if action.x else None
        y = int(action.y / config.capture_scale) if action.y else None

        pag.scroll(amount, x=x, y=y)
        return f"Scrolled {action.direction} by {abs(amount)}"

    def _do_move(self, pag, action: Action) -> str:
        """Move the mouse cursor."""
        if action.x is None or action.y is None:
            return "Error: move requires x and y coordinates"

        x = int(action.x / config.capture_scale)
        y = int(action.y / config.capture_scale)
        pag.moveTo(x, y, duration=0.3)
        return f"Moved mouse to ({x}, {y})"

    def _do_wait(self, action: Action) -> str:
        """Wait/pause."""
        duration = min(action.seconds, 10.0)
        time.sleep(duration)
        return f"Waited {duration}s"
