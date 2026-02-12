"""
Watchtower Agent - Entry Point
Lightweight local agent that captures the screen and streams it to the cloud server.
On first run, prompts the user for their connection token.
"""

import asyncio
import logging
import sys
import os

# Ensure the agent directory is on the import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import agent_config, AgentConfig, CONFIG_FILE, LOG_FILE

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("watchtower-agent")


def first_run_setup() -> bool:
    """
    Show a setup dialog for first-time configuration.
    Returns True if setup was completed, False if cancelled.
    """
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        # Fallback to console input if tkinter not available
        return _console_setup()

    return _gui_setup()


def _gui_setup() -> bool:
    """GUI setup dialog using tkinter."""
    import tkinter as tk
    import webbrowser

    completed = False

    root = tk.Tk()
    root.title("Watchtower Agent Setup")
    root.geometry("520x420")
    root.resizable(False, False)
    root.configure(bg="#1a1a2e")

    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 260
    y = (root.winfo_screenheight() // 2) - 210
    root.geometry(f"+{x}+{y}")

    # Title
    tk.Label(
        root, text="Watchtower Agent", font=("Segoe UI", 18, "bold"),
        bg="#1a1a2e", fg="#e0e0e0",
    ).pack(pady=(20, 5))

    tk.Label(
        root, text="Connect this agent to your Watchtower cloud account",
        font=("Segoe UI", 10), bg="#1a1a2e", fg="#888",
    ).pack(pady=(0, 15))

    # Server URL
    tk.Label(
        root, text="Server URL", font=("Segoe UI", 10, "bold"),
        bg="#1a1a2e", fg="#c0c0c0", anchor="w",
    ).pack(fill="x", padx=40)

    server_entry = tk.Entry(
        root, font=("Consolas", 11), bg="#16213e", fg="#e0e0e0",
        insertbackground="#e0e0e0", relief="flat", bd=0,
        highlightthickness=1, highlightcolor="#0f3460", highlightbackground="#333",
    )
    server_entry.pack(fill="x", padx=40, pady=(2, 10), ipady=6)
    server_entry.insert(0, agent_config.server_url or "wss://your-app.up.railway.app/ws/agent")

    # Connection Token
    tk.Label(
        root, text="Connection Token", font=("Segoe UI", 10, "bold"),
        bg="#1a1a2e", fg="#c0c0c0", anchor="w",
    ).pack(fill="x", padx=40)

    token_entry = tk.Entry(
        root, font=("Consolas", 11), bg="#16213e", fg="#e0e0e0",
        insertbackground="#e0e0e0", relief="flat", bd=0, show="*",
        highlightthickness=1, highlightcolor="#0f3460", highlightbackground="#333",
    )
    token_entry.pack(fill="x", padx=40, pady=(2, 5), ipady=6)

    # Show/hide toggle
    show_var = tk.BooleanVar(value=False)

    def toggle_show():
        token_entry.config(show="" if show_var.get() else "*")

    tk.Checkbutton(
        root, text="Show token", variable=show_var, command=toggle_show,
        bg="#1a1a2e", fg="#888", selectcolor="#16213e",
        activebackground="#1a1a2e", activeforeground="#888",
        font=("Segoe UI", 9),
    ).pack(anchor="w", padx=40)

    # Instructions
    instructions = tk.Label(
        root,
        text="Get your connection token from the Watchtower dashboard:\nSettings → Agent → Generate Connection Token",
        font=("Segoe UI", 9), bg="#1a1a2e", fg="#666",
        justify="left",
    )
    instructions.pack(fill="x", padx=40, pady=(10, 0))

    # Error label
    error_label = tk.Label(
        root, text="", font=("Segoe UI", 9), bg="#1a1a2e", fg="#e74c3c",
    )
    error_label.pack(fill="x", padx=40)

    # Buttons
    btn_frame = tk.Frame(root, bg="#1a1a2e")
    btn_frame.pack(fill="x", padx=40, pady=(10, 20))

    def on_connect():
        nonlocal completed
        server_url = server_entry.get().strip()
        token = token_entry.get().strip()

        if not server_url:
            error_label.config(text="Server URL is required")
            return
        if not token:
            error_label.config(text="Connection token is required")
            return
        if not server_url.startswith(("ws://", "wss://")):
            error_label.config(text="Server URL must start with ws:// or wss://")
            return

        agent_config.server_url = server_url
        agent_config.connection_token = token
        agent_config.save()
        completed = True
        root.destroy()

    def on_cancel():
        root.destroy()

    tk.Button(
        btn_frame, text="Connect", font=("Segoe UI", 11, "bold"),
        bg="#0f3460", fg="white", relief="flat", bd=0,
        activebackground="#1a5276", activeforeground="white",
        cursor="hand2", command=on_connect, width=12,
    ).pack(side="right", padx=(10, 0))

    tk.Button(
        btn_frame, text="Cancel", font=("Segoe UI", 11),
        bg="#333", fg="#ccc", relief="flat", bd=0,
        activebackground="#444", activeforeground="#ccc",
        cursor="hand2", command=on_cancel, width=12,
    ).pack(side="right")

    root.mainloop()
    return completed


def _console_setup() -> bool:
    """Fallback console setup if tkinter is not available."""
    print("\n=== Watchtower Agent Setup ===\n")
    print("Get your connection details from the Watchtower dashboard.")
    print("Settings → Agent → Generate Connection Token\n")

    server_url = input("Server URL (e.g., wss://your-app.up.railway.app/ws/agent): ").strip()
    if not server_url:
        print("Cancelled.")
        return False

    token = input("Connection Token: ").strip()
    if not token:
        print("Cancelled.")
        return False

    agent_config.server_url = server_url
    agent_config.connection_token = token
    agent_config.save()
    return True


async def run_agent():
    """Main agent loop."""
    from capture import ScreenCapture
    from input_control import InputController
    from ws_client import AgentWSClient
    from tray import TrayIcon

    logger.info("Starting Watchtower Agent...")
    logger.info(f"Config file: {CONFIG_FILE}")
    logger.info(f"Server: {agent_config.server_url}")

    # Initialize components
    capture = ScreenCapture()
    input_controller = InputController()

    # Create WebSocket client
    ws_client = AgentWSClient(
        capture=capture,
        input_controller=input_controller,
    )

    # Create system tray icon
    tray = TrayIcon(
        on_pause=lambda: capture.pause(),
        on_resume=lambda: capture.resume(),
        on_quit=lambda: asyncio.get_event_loop().call_soon_threadsafe(_shutdown),
        on_toggle_actions=lambda enabled: (
            input_controller.enable() if enabled else input_controller.disable()
        ),
    )

    # Wire up status changes to tray
    def on_ws_status(status):
        tray.set_status(status)

    ws_client.on_status_change = on_ws_status

    shutdown_event = asyncio.Event()

    def _shutdown():
        shutdown_event.set()

    # Start everything
    tray.start()
    await capture.start()

    # Run WebSocket client and wait for shutdown
    ws_task = asyncio.create_task(ws_client.start())

    try:
        await shutdown_event.wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        logger.info("Shutting down...")
        await ws_client.stop()
        await capture.stop()
        tray.stop()
        ws_task.cancel()
        try:
            await ws_task
        except asyncio.CancelledError:
            pass

    logger.info("Agent stopped.")


def main():
    """Entry point."""
    logger.info("Watchtower Agent starting...")

    # Check if first-time setup is needed
    if not agent_config.is_configured:
        logger.info("First run — showing setup dialog")
        if not first_run_setup():
            logger.info("Setup cancelled, exiting.")
            sys.exit(0)

    # Validate config
    try:
        agent_config.validate()
    except ValueError as e:
        logger.error(f"Invalid config: {e}")
        # Re-show setup
        if not first_run_setup():
            sys.exit(1)
        agent_config.validate()

    # Run the async agent
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
