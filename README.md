# Watchtower AI — React + FastAPI Edition

A real-time screen-sharing agent built with **React + Tailwind** (frontend) and **FastAPI** (backend).

## Quick Start

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your API key
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Run the server
```bash
python server.py
```

The React frontend is **pre-built** in `frontend/dist/` — the server serves it automatically. Open `http://localhost:8765`.

## Development (modify the React UI)

If you want to edit the frontend:

```bash
cd frontend
npm install
npm run dev       # starts Vite dev server on :3000 with proxy to :8765
```

Then in another terminal:
```bash
python server.py  # backend on :8765
```

Vite will proxy `/api/*` and `/ws/*` requests to the FastAPI backend automatically.

When you're done, build for production:
```bash
cd frontend
npm run build     # outputs to frontend/dist/
```

## Project Structure

```
watchtower-ai/
├── server.py              # FastAPI server (serves React build + WebSockets + API)
├── agent.py               # Claude API conversation manager
├── capture.py             # Screen capture with change detection
├── input_control.py       # Mouse/keyboard action execution
├── config.py              # Configuration (env vars)
├── mcp_server.py          # MCP server for Claude Desktop
├── requirements.txt       # Python dependencies
└── frontend/
    ├── package.json       # Node dependencies
    ├── vite.config.js     # Vite + Tailwind + dev proxy config
    ├── index.html         # HTML shell
    ├── src/
    │   ├── main.jsx       # React entry point
    │   ├── App.jsx        # Main app component (all UI)
    │   └── index.css      # Tailwind import
    └── dist/              # Pre-built production files (served by FastAPI)
        ├── index.html
        └── assets/
```
