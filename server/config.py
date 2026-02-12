"""
Watchtower AI - Server Configuration
All settings can be overridden via environment variables.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ServerConfig:
    # == Anthropic API ==
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    # == Server ==
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8765"))

    # == Database ==
    database_url: str = os.getenv("DATABASE_URL", "sqlite:////app/watchtower.db")

    # == JWT Auth ==
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

    # == Stripe Billing ==
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_price_pro: str = os.getenv("STRIPE_PRICE_PRO", "")
    stripe_price_team: str = os.getenv("STRIPE_PRICE_TEAM", "")

    # == Agent / Conversation ==
    max_conversation_frames: int = int(os.getenv("MAX_CONVERSATION_FRAMES", "10"))
    max_conversation_turns: int = int(os.getenv("MAX_CONVERSATION_TURNS", "50"))
    system_prompt: str = os.getenv("SYSTEM_PROMPT", "")
    action_delay: float = float(os.getenv("ACTION_DELAY", "0.5"))

    def validate(self):
        import logging
        logger = logging.getLogger(__name__)
        if not self.anthropic_api_key:
            logger.warning("ANTHROPIC_API_KEY not set — Claude chat will not work until configured.")
        return self

    @property
    def default_system_prompt(self) -> str:
        return self.system_prompt or SYSTEM_PROMPT


SYSTEM_PROMPT = '''You are Watchtower AI, an AI assistant with live visual access to the user's computer screen. You can see real-time screenshots of their display.

## Your Capabilities
- You receive periodic screenshots of the user's screen
- You can analyze what's visible: applications, text, UI elements, errors, etc.
- When action execution is enabled, you can control the mouse, keyboard, and run commands

## How to Respond
- Describe what you see when asked
- Proactively notice errors, issues, or things that seem off
- When helping with tasks, reference specific UI elements you can see
- Be concise - you're in a live session, not writing an essay

## Action Format
When you need to perform actions on the computer, include them as a JSON block:

```actions
[
  {"type": "click", "x": 500, "y": 300, "button": "left"},
  {"type": "type", "text": "hello world"},
  {"type": "key", "keys": "ctrl+s"},
  {"type": "scroll", "x": 500, "y": 400, "direction": "down", "amount": 3},
  {"type": "move", "x": 200, "y": 150},
  {"type": "screenshot"},
  {"type": "wait", "seconds": 2}
]
```

Only include action blocks when the user asks you to do something or when you need to interact with the screen. Always explain what you're about to do before doing it.

## Important
- Never interact with sensitive fields (passwords, banking) even if asked
- Ask for confirmation before destructive actions
- If you're unsure what you're seeing, say so
'''


server_config = ServerConfig()
