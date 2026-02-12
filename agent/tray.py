"""
Watchtower Agent - System Tray Icon
Provides a minimal system tray UI showing connection status with pause/quit controls.
"""

import logging
import threading
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Lazy imports — pystray and PIL may not be available in all environments
_pystray = None
_PILImage = None


def _load_deps():
    global _pystray, _PILImage
    if _pystray is None:
        import pystray
        from PIL import Image as PILImage
        _pystray = pystray
        _PILImage = PILImage


# Status colors
STATUS_COLORS = {
    "connected": (0, 200, 80),       # Green
    "connecting": (255, 180, 0),      # Yellow/Orange
    "disconnected": (180, 180, 180),  # Gray
    "auth_failed": (220, 50, 50),     # Red
    "error": (220, 50, 50),           # Red
    "paused": (100, 150, 255),        # Blue
}

STATUS_LABELS = {
    "connected": "Connected",
    "connecting": "Connecting...",
    "disconnected": "Disconnected",
    "auth_failed": "Auth Failed",
    "error": "Error",
    "paused": "Paused",
}


def _create_icon_image(color: tuple, size: int = 64) -> "PILImage.Image":
    """Create a simple colored circle icon."""
    _load_deps()
    img = _PILImage.new("RGBA", (size, size), (0, 0, 0, 0))

    # Draw a filled circle
    cx, cy = size // 2, size // 2
    radius = size // 2 - 2
    for x in range(size):
        for y in range(size):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy <= radius * radius:
                img.putpixel((x, y), (*color, 255))

    return img


class TrayIcon:
    """
    System tray icon with status indicator and basic controls.

    Usage:
        tray = TrayIcon(
            on_pause=my_pause_func,
            on_resume=my_resume_func,
            on_quit=my_quit_func,
        )
        tray.start()
        tray.set_status("connected")
        ...
        tray.stop()
    """

    def __init__(
        self,
        on_pause: Optional[Callable] = None,
        on_resume: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
        on_toggle_actions: Optional[Callable[[bool], None]] = None,
    ):
        _load_deps()

        self._on_pause = on_pause
        self._on_resume = on_resume
        self._on_quit = on_quit
        self._on_toggle_actions = on_toggle_actions

        self._status = "disconnected"
        self._paused = False
        self._actions_enabled = False
        self._icon: Optional[_pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start the tray icon in a background thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def set_status(self, status: str):
        """Update the tray icon status."""
        self._status = status
        self._update_icon()

    def set_paused(self, paused: bool):
        """Update paused state."""
        self._paused = paused
        self._update_icon()

    def set_actions_enabled(self, enabled: bool):
        """Update actions enabled state."""
        self._actions_enabled = enabled
        self._update_icon()

    def _run(self):
        """Run the tray icon (blocking, runs in thread)."""
        menu = self._build_menu()
        color = STATUS_COLORS.get(self._status, (180, 180, 180))
        icon_image = _create_icon_image(color)

        self._icon = _pystray.Icon(
            "watchtower-agent",
            icon_image,
            "Watchtower Agent",
            menu,
        )

        self._icon.run()

    def _build_menu(self) -> "_pystray.Menu":
        """Build the context menu."""
        MenuItem = _pystray.MenuItem

        status_text = STATUS_LABELS.get(self._status, self._status)

        items = [
            MenuItem(f"Watchtower Agent — {status_text}", None, enabled=False),
            _pystray.Menu.SEPARATOR,
        ]

        # Pause/Resume toggle
        if self._paused:
            items.append(MenuItem("Resume Capture", self._on_resume_click))
        else:
            items.append(MenuItem("Pause Capture", self._on_pause_click))

        # Actions toggle
        if self._actions_enabled:
            items.append(MenuItem("Disable Actions", self._on_disable_actions))
        else:
            items.append(MenuItem("Enable Actions", self._on_enable_actions))

        items.extend([
            _pystray.Menu.SEPARATOR,
            MenuItem("Quit", self._on_quit_click),
        ])

        return _pystray.Menu(*items)

    def _update_icon(self):
        """Update the icon image and menu."""
        if not self._icon:
            return

        try:
            color = STATUS_COLORS.get(self._status, (180, 180, 180))
            self._icon.icon = _create_icon_image(color)
            self._icon.menu = self._build_menu()

            status_text = STATUS_LABELS.get(self._status, self._status)
            self._icon.title = f"Watchtower Agent — {status_text}"
        except Exception as e:
            logger.error(f"Failed to update tray icon: {e}")

    def _on_pause_click(self, icon, item):
        self._paused = True
        if self._on_pause:
            self._on_pause()
        self._update_icon()

    def _on_resume_click(self, icon, item):
        self._paused = False
        if self._on_resume:
            self._on_resume()
        self._update_icon()

    def _on_enable_actions(self, icon, item):
        self._actions_enabled = True
        if self._on_toggle_actions:
            self._on_toggle_actions(True)
        self._update_icon()

    def _on_disable_actions(self, icon, item):
        self._actions_enabled = False
        if self._on_toggle_actions:
            self._on_toggle_actions(False)
        self._update_icon()

    def _on_quit_click(self, icon, item):
        if self._on_quit:
            self._on_quit()
        self.stop()
