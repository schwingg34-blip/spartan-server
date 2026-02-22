import json
import asyncio
from datetime import datetime
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Spartan SMC Server")

# Allow all origins (dashboard connects from browser)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── SIGNAL STORE ─────────────────────────────────────────────
# Keeps last 50 signals in memory
signal_history: List[dict] = []
MAX_HISTORY = 50

# ── WEBSOCKET MANAGER ─────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        print(f"[WS] Client connected. Total: {len(self.active)}")
        # Send full history to new client immediately
        if signal_history:
            await ws.send_json({"type": "history", "signals": signal_history})

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        print(f"[WS] Client disconnected. Total: {len(self.active)}")

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()

# ── WEBHOOK ENDPOINT (TradingView posts here) ─────────────────
@app.post("/webhook")
async def receive_webhook(request: Request):
    try:
        body = await request.body()
        raw  = body.decode("utf-8").strip()
        print(f"[WEBHOOK] Received: {raw}")

        # TradingView sends JSON string
        data = json.loads(raw)

        # Determine message type
        msg_type = data.get("type", "signal")

        if msg_type == "OVERRIDE":
            event = {
                "type":     "override",
                "time":     datetime.now().strftime("%H:%M:%S"),
                "contract": data.get("contract", "?"),
                "bull":     data.get("bull", 0),
                "bear":     data.get("bear", 0),
            }
            await manager.broadcast({"type": "override", "data": event})
            return JSONResponse({"status": "ok", "type": "override"})

        # Build signal object
        signal = {
            "id":        datetime.now().strftime("%H%M%S%f"),
            "time":      datetime.now().strftime("%H:%M:%S"),
            "contract":  data.get("contract",  "?"),
            "asset":     data.get("asset",     "Futures"),
            "direction": data.get("direction", "LONG"),
            "strength":  data.get("strength",  "MODERATE"),
            "score":     int(data.get("score", 0)),
            "entry":     float(data.get("entry", 0)),
            "sl":        float(data.get("sl",    0)),
            "tp1":       float(data.get("tp1",   0)),
            "tp2":       float(data.get("tp2",   0)),
            "doubt":     data.get("doubt", "false") == "true",
            "htf":       data.get("htf",   "neutral"),
            "volSpike":  data.get("volSpike", "false") == "true",
            "bos":       data.get("bos",   "false") == "true",
            "choch":     data.get("choch", "false") == "true",
            "bullFVG":   data.get("bullFVG","false") == "true",
            "bearFVG":   data.get("bearFVG","false") == "true",
        }

        # Add to history (newest first)
        signal_history.insert(0, signal)
        if len(signal_history) > MAX_HISTORY:
            signal_history.pop()

        # Broadcast to all connected dashboards
        await manager.broadcast({"type": "signal", "data": signal})
        print(f"[SIGNAL] {signal['direction']} {signal['strength']} {signal['contract']} score={signal['score']}")

        return JSONResponse({"status": "ok", "signal_id": signal["id"]})

    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse failed: {e} | raw: {raw}")
        return JSONResponse({"status": "error", "msg": "invalid JSON"}, status_code=400)
    except Exception as e:
        print(f"[ERROR] {e}")
        return JSONResponse({"status": "error", "msg": str(e)}, status_code=500)

# ── WEBSOCKET ENDPOINT (dashboard connects here) ──────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            # Keep alive — ping every 20s
            await asyncio.sleep(20)
            try:
                await ws.send_json({"type": "ping"})
            except Exception:
                break
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)

# ── HEALTH CHECK ──────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status":       "ok",
        "signals_stored": len(signal_history),
        "ws_clients":   len(manager.active),
        "time":         datetime.now().isoformat(),
    }

# ── SIGNAL HISTORY API ────────────────────────────────────────
@app.get("/signals")
async def get_signals():
    return JSONResponse({"signals": signal_history})

# ── DASHBOARD (served from root) ──────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    try:
        with open("dashboard.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Dashboard not found. Place dashboard.html in the project root.</h1>"

# ── ENTRYPOINT ────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
