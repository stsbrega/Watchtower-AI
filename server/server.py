"""
Watchtower AI - Cloud Server
FastAPI application serving the React frontend, handling WebSocket relay
between local agents and browser clients, and managing Claude conversations.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from server.config import server_config
from server.db import init_database, db_middleware
from server.session_manager import SessionManager
from server.ws_agent import handle_agent_ws
from server.ws_browser import handle_browser_stream_ws, handle_browser_chat_ws
from server.saas.routes import router as saas_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Watchtower AI Cloud Server starting up...")
    server_config.validate()
    init_database()
    logger.info(f"Server available at http://{server_config.host}:{server_config.port}")
    yield
    logger.info("Watchtower AI Cloud Server shut down")


app = FastAPI(title="Watchtower AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(db_middleware)

# Mount SaaS routes (auth, billing, usage)
app.include_router(saas_router)


# ── Static Files / Frontend ─────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend" / "dist"

if FRONTEND_DIR.exists():
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        logger.info(f"Mounted frontend assets from {assets_dir}")
else:
    logger.warning(f"Frontend not built: {FRONTEND_DIR}")


@app.get("/", response_class=HTMLResponse)
async def index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file, media_type="text/html")
    return HTMLResponse(
        "<h1>Frontend not built</h1><p>Run <code>cd frontend && npm run build</code></p>",
        status_code=503,
    )


# ── API Routes ───────────────────────────────────────────────────────

@app.get("/api/status")
async def status():
    return {
        "status": "ok",
        "sessions": session_manager.get_stats(),
    }


# ── WebSocket Endpoints ──────────────────────────────────────────────

@app.websocket("/ws/agent")
async def ws_agent(websocket: WebSocket):
    await handle_agent_ws(websocket, session_manager)


@app.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket):
    await handle_browser_stream_ws(websocket, session_manager)


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await handle_browser_chat_ws(websocket, session_manager)


# ── Catch-all for SPA routing ────────────────────────────────────────

@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """Serve index.html for all unmatched routes (SPA client-side routing)."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file, media_type="text/html")
    return HTMLResponse("Not found", status_code=404)


# ── Entry Point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print(r"""
   ╔══════════════════════════════════════════╗
   ║       Watchtower AI Cloud Server         ║
   ║        SaaS + Agent Architecture         ║
   ╚══════════════════════════════════════════╝
    """)
    uvicorn.run(
        "server.server:app",
        host=server_config.host,
        port=server_config.port,
        reload=False,
        log_level="info",
    )
