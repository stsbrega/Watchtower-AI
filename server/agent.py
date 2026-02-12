"""
Watchtower AI - Cloud Agent
Manages conversation with Claude API. Receives frames from the session
(not from local capture) and returns actions (not executed locally).
"""

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import anthropic

from server.config import server_config

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    role: str
    text: str
    frames: list[str] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Action:
    """Parsed action from Claude's response."""
    type: str
    x: Optional[int] = None
    y: Optional[int] = None
    button: str = "left"
    text: Optional[str] = None
    keys: Optional[str] = None
    direction: str = "down"
    amount: int = 3
    seconds: float = 1.0

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
        action_type = d.get("type")
        if not action_type:
            return None
        valid_types = {"click", "type", "key", "scroll", "move", "screenshot", "wait"}
        if action_type not in valid_types:
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
            seconds=min(d.get("seconds", 1.0), 10.0),
        )


class Agent:
    """
    Cloud-side agent that manages Claude conversation.
    Receives frames from the session, returns actions to be dispatched
    to the local agent (not executed here).
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=server_config.anthropic_api_key)
        self.conversation: list[ConversationTurn] = []

    async def chat(self, user_message: str, frame_b64: Optional[str] = None) -> dict:
        content = []
        frames_attached = []

        if frame_b64:
            frames_attached = [frame_b64]
            content.append({
                "type": "text",
                "text": "[Screen capture 1 of 1]",
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": frame_b64,
                },
            })

        content.append({"type": "text", "text": user_message})

        self.conversation.append(ConversationTurn(
            role="user",
            text=user_message,
            frames=frames_attached,
        ))

        messages = self._build_messages()

        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=server_config.model,
                max_tokens=4096,
                system=server_config.default_system_prompt,
                messages=messages,
            )
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return {
                "text": f"API Error: {e.message}",
                "actions": [],
                "frame_count": len(frames_attached),
                "tokens_used": {"input": 0, "output": 0},
            }

        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text += block.text

        actions = self._parse_actions(response_text)
        display_text = self._clean_response_text(response_text)

        self.conversation.append(ConversationTurn(
            role="assistant",
            text=display_text,
            actions=[a.to_dict() for a in actions],
        ))

        self._trim_conversation()

        return {
            "text": display_text,
            "actions": [a.to_dict() for a in actions],
            "frame_count": len(frames_attached),
            "tokens_used": {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
            },
        }

    def reset_conversation(self):
        self.conversation.clear()
        logger.info("Conversation reset")

    def get_conversation_summary(self) -> dict:
        return {
            "turns": len(self.conversation),
            "total_frames_sent": sum(len(t.frames) for t in self.conversation),
            "total_actions": sum(len(t.actions) for t in self.conversation),
        }

    def _build_messages(self) -> list[dict]:
        messages = []
        frame_budget = server_config.max_conversation_frames

        turns_with_frames = []
        for turn in reversed(self.conversation):
            if turn.role == "user" and turn.frames:
                frames_to_include = min(len(turn.frames), frame_budget)
                frame_budget -= frames_to_include
                turns_with_frames.append((id(turn), frames_to_include))

        turns_frame_map = dict(turns_with_frames)

        for turn in self.conversation:
            if turn.role == "user":
                content = []
                frame_count = turns_frame_map.get(id(turn), 0)
                for frame_b64 in turn.frames[:frame_count]:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": frame_b64,
                        },
                    })
                content.append({"type": "text", "text": turn.text})
                messages.append({"role": "user", "content": content})
            elif turn.role == "assistant":
                messages.append({"role": "assistant", "content": turn.text})

        return messages

    def _parse_actions(self, response_text: str) -> list[Action]:
        actions = []
        pattern = r"```actions\s*\n(.*?)```"
        matches = re.findall(pattern, response_text, re.DOTALL)
        for match in matches:
            try:
                action_list = json.loads(match.strip())
                if isinstance(action_list, list):
                    for action_dict in action_list:
                        action = Action.from_dict(action_dict)
                        if action:
                            actions.append(action)
                elif isinstance(action_list, dict):
                    action = Action.from_dict(action_list)
                    if action:
                        actions.append(action)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse action block: {e}")
        return actions

    def _clean_response_text(self, text: str) -> str:
        cleaned = re.sub(r"```actions\s*\n.*?```", "", text, flags=re.DOTALL)
        return cleaned.strip()

    def _trim_conversation(self):
        max_turns = server_config.max_conversation_turns
        if len(self.conversation) > max_turns:
            excess = len(self.conversation) - max_turns
            self.conversation = self.conversation[excess:]
