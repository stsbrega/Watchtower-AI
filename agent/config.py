"""
Watchtower Agent - Local Configuration
Stores connection token and capture settings in %APPDATA%/WatchtowerAgent/config.json
"""

import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_config_dir() -> Path:
    """Get the platform-appropriate config directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    config_dir = base / "WatchtowerAgent"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


CONFIG_DIR = _get_config_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE = CONFIG_DIR / "agent.log"


@dataclass
class AgentConfig:
    # == Connection ==
    server_url: str = ""              # e.g., "wss://watchtower-ai.up.railway.app/ws/agent"
    connection_token: str = ""        # API key / connection token from the web dashboard

    # == Screen Capture ==
    capture_fps: float = 2.0
    capture_quality: int = 65
    capture_scale: float = 0.5
    change_threshold: float = 0.02
    max_frame_width: int = 1280
    max_frame_height: int = 720

    # == Action Execution ==
    action_execution: bool = False
    action_delay: float = 0.5

    # == Privacy ==
    blur_regions: list = field(default_factory=list)

    # == Reconnection ==
    reconnect_delay: float = 3.0
    max_reconnect_delay: float = 60.0
    reconnect_backoff: float = 1.5

    def save(self):
        """Save config to disk."""
        data = asdict(self)
        try:
            CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info(f"Config saved to {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    @classmethod
    def load(cls) -> "AgentConfig":
        """Load config from disk, or return defaults."""
        if not CONFIG_FILE.exists():
            logger.info("No config file found, using defaults")
            return cls()

        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            # Only use known fields
            known_fields = {f.name for f in cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in known_fields}
            return cls(**filtered)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return cls()

    @property
    def is_configured(self) -> bool:
        """Check if the agent has a server URL and connection token."""
        return bool(self.server_url) and bool(self.connection_token)

    def validate(self):
        """Validate config values."""
        errors = []
        if not self.server_url:
            errors.append("Server URL is required.")
        if not self.connection_token:
            errors.append("Connection token is required.")
        if not 1 <= self.capture_quality <= 100:
            errors.append("Capture quality must be between 1 and 100.")
        if not 0.1 <= self.capture_scale <= 1.0:
            errors.append("Capture scale must be between 0.1 and 1.0.")
        if errors:
            raise ValueError("\n".join(errors))
        return self


# Global config instance
agent_config = AgentConfig.load()
