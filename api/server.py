"""
FastAPI server — serves the frontend and handles the WebSocket session.

WebSocket protocol:
  Client → Server:
    {"type": "start", "username": "...", "num_games": 10, "time_control": "blitz"}
    {"type": "answer", "id": "question_id", "value": "user answer"}

  Server → Client:
    {"type": "debug",    "message": "..."}
    {"type": "node",     "node": "analyst|coach|critic", "status": "active|complete|waiting"}
    {"type": "stream",   "agent": "analyst|coach|critic", "text": "..."}
    {"type": "speak",    "text": "..."}
    {"type": "question", "id": "...", "question": "...", "options": [...]}
    {"type": "complete", "md_path": "...", "pdf_path": "..."}
    {"type": "error",    "message": "..."}
"""
import asyncio
import queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
OUTPUTS_DIR = BASE_DIR / "outputs"

class RemoveFrameOptionsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        try:
            del response.headers["X-Frame-Options"]
        except KeyError:
            pass
        response.headers["Content-Security-Policy"] = "frame-ancestors *"
        return response


app = FastAPI(title="Chess Coach Agent")
app.add_middleware(RemoveFrameOptionsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
executor = ThreadPoolExecutor(max_workers=2)


@app.get("/")
async def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/play")
async def play_page():
    return FileResponse(str(FRONTEND_DIR / "play.html"))


@app.get("/practice")
async def practice_page():
    return FileResponse(str(FRONTEND_DIR / "practice.html"))


@app.get("/reports")
async def reports_page():
    return FileResponse(str(FRONTEND_DIR / "reports.html"))


@app.get("/api/reports")
async def list_reports():
    """Return metadata for all saved coaching report .md files, newest first."""
    from datetime import datetime
    OUTPUTS_DIR.mkdir(exist_ok=True)
    results = []
    for f in sorted(OUTPUTS_DIR.glob("*_report_*.md"),
                    key=lambda x: x.stat().st_mtime, reverse=True):
        stat = f.stat()
        stem  = f.stem                          # e.g. JagerBombEnjoyer_report_20260504_190853
        parts = stem.split("_report_", 1)
        username  = parts[0] if len(parts) == 2 else stem
        ts_raw    = parts[1] if len(parts) == 2 else ""
        try:
            dt = datetime.strptime(ts_raw, "%Y%m%d_%H%M%S")
            date_str = dt.strftime("%b %d, %Y  %H:%M")
        except ValueError:
            date_str = datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y  %H:%M")
        results.append({
            "filename": f.name,
            "username": username,
            "date":     date_str,
            "size_kb":  round(stat.st_size / 1024, 1),
            "pdf":      f.with_suffix(".pdf").name if f.with_suffix(".pdf").exists() else None,
        })
    return JSONResponse(results)


@app.get("/api/report-content/{filename}")
async def get_report_content(filename: str):
    """Return the raw markdown text of a saved report."""
    if ".." in filename or "/" in filename or not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = OUTPUTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404)
    return JSONResponse({"content": path.read_text(encoding="utf-8")})


@app.get("/outputs/{filename}")
async def serve_output(filename: str):
    path = OUTPUTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(str(path))


@app.websocket("/ws/game")
async def game_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        config = await websocket.receive_json()
        from api.routes.play import run_game
        await run_game(websocket, config)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass


@app.websocket("/ws/practice")
async def practice_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        msg = await websocket.receive_json()
        username = msg.get("username", "")
        mode     = msg.get("mode", "puzzles")

        from api.routes.practice import generate_puzzles, generate_opening_lines
        if mode == "puzzles":
            result = await generate_puzzles(username)
            # result is {"puzzles": [...], "source": "games"|"none", "message": "..."}
            await websocket.send_json({
                "type":    "puzzles",
                "data":    result["puzzles"],
                "source":  result.get("source", "none"),
                "message": result.get("message", ""),
            })
        elif mode == "openings":
            data = await generate_opening_lines(username)
            await websocket.send_json({"type": "openings", "data": data})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    event_q: queue.Queue = queue.Queue()
    input_q: queue.Queue = queue.Queue()

    try:
        # First message must be the session config
        start_data = await websocket.receive_json()

        from utils.events import bus
        bus.setup_web(event_q, input_q)

        from api.session import run_session
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(executor, run_session, start_data)

        # Bridge loop: relay events to client, relay answers to graph
        while True:
            # Drain events from graph → send to client
            while not event_q.empty():
                event = event_q.get_nowait()
                await websocket.send_json(event)

            # Graph finished?
            if future.done() and event_q.empty():
                try:
                    future.result()
                except Exception as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                break

            # Check for incoming answer from client (non-blocking)
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=0.05)
                if msg.get("type") == "answer":
                    input_q.put(msg.get("value", ""))
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break

            await asyncio.sleep(0.02)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        from utils.events import bus
        bus.setup_cli()


def start(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run(app, host=host, port=port, log_level="warning")
