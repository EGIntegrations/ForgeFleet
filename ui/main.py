from __future__ import annotations

import os, json, pathlib, subprocess, datetime as dt
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

# ─── Redis ──────────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r         = aioredis.from_url(REDIS_URL, decode_responses=True)

AGENTS = os.getenv("AGENTS", "DemoAgent,SupportAgent,SwiftAgent,GitAgent").split(",")
AGENTS = [a.strip() for a in AGENTS if a.strip()]

# 👇 THIS must be present *before* any route that uses it
SUG_KEYS = {a: f"suggestions:{a}" for a in AGENTS}

# ─── GitHub settings ( .env ) ───────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "")
REMOTE_URL   = (
    f"https://{GITHUB_TOKEN}@github.com/{GITHUB_OWNER}/{GITHUB_REPO}.git"
    if GITHUB_TOKEN and GITHUB_OWNER and GITHUB_REPO else ""
)

REPO_ROOT = pathlib.Path(os.getenv("REPO_ROOT", "/workspace/repo")).expanduser()
REPO_ROOT.mkdir(parents=True, exist_ok=True)  # ensure path exists

def _git_safe(*cmd: str):
    try:
        subprocess.run(["git", *cmd], cwd=REPO_ROOT,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=True)
    except Exception:
        pass

# ─── Clone / init repo once on startup ──────────────────────────────────
if REMOTE_URL:
    if not (REPO_ROOT / ".git").exists():
        res = subprocess.run(
            ["git", "clone", REMOTE_URL, str(REPO_ROOT)],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )
        if res.returncode != 0:
            print("⚠️  Clone failed, initialising repo in‑place", flush=True)
            _git_safe("init")
            _git_safe("remote", "add", "origin", REMOTE_URL)
            _git_safe("fetch", "origin")
            _git_safe("checkout", "-B", "main")
    else:
        print(f"⬇️  Pulling latest into {REPO_ROOT}", flush=True)

    _git_safe("config", "user.name", os.getenv("GIT_USER", "forgefleet‑bot"))
    _git_safe("config", "user.email", os.getenv("GIT_EMAIL", "bot@forgefleet"))

# ─── FastAPI / templates  ───────────────────────────────────────────────
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
env = Environment(loader=FileSystemLoader("templates"))

@app.get("/", response_class=HTMLResponse)
async def index():
    q = {a: await r.llen(f"queue:{a}") for a in AGENTS}
    return HTMLResponse(env.get_template("index.html").render(agents=AGENTS, queues=q))

@app.get("/api/queues", response_class=JSONResponse)
async def api_queues():
    return {"queues": {a: await r.llen(f"queue:{a}") for a in AGENTS}}

@app.post("/cmd/{agent}", response_class=JSONResponse)
async def cmd_agent(agent: str, req: Request):
    await r.lpush(f"queue:{agent}", json.dumps(await req.json()))
    return {"status": "queued"}

@app.websocket("/ws/{agent}")
async def ws_logs(ws: WebSocket, agent: str):
    await ws.accept()
    ps = r.pubsub()
    await ps.subscribe(f"logs:{agent}")
    try:
        async for msg in ps.listen():
            if msg["type"] == "message":
                await ws.send_text(msg["data"])
    except WebSocketDisconnect:
        await ps.unsubscribe(f"logs:{agent}")

# ─── suggestions helpers ────────────────────────────────────────────────
async def _publish(txt: str):
    await r.publish("logs:SupportAgent", json.dumps({"type": "message", "data": txt}))

@app.get("/suggestions/json", response_class=JSONResponse)
async def suggestions_json():
    """
    Return *all* pending suggestions – anything that’s still in the old
    global list called  “suggestions” *plus* anything in the new
    per‑agent lists, e.g.  suggestions:SwiftAgent, suggestions:DemoAgent …
    """
    # the legacy list:
    keys = ["suggestions"]

    # the new per‑agent lists:
    keys += list(SUG_KEYS.values())

    items: list[str] = []
    for k in keys:
        items.extend(await r.lrange(k, 0, -1))

    # newest first
    return [json.loads(x) for x in items[::-1]]


# ─── accept a suggestion ────────────────────────────────────────────────
@app.post("/suggestions/{sid}/accept", response_class=JSONResponse)
async def accept_suggestion(sid: str):
    for key in SUG_KEYS.values():                     # search every list
        for raw in await r.lrange(key, 0, -1):
            s = json.loads(raw)
            if s["id"] != sid:
                continue

            fp = REPO_ROOT / s["path"]
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(s["content"], encoding="utf-8")

            if REMOTE_URL:
                rel   = str(fp.relative_to(REPO_ROOT))
                stamp = dt.datetime.utcnow().strftime("%Y‑%m‑%d %H:%M:%S")
                _git_safe("add", rel)
                _git_safe("commit", "-m", f"{stamp} ✅ {rel}")
                _git_safe("push", "origin", "main")

            # remove the accepted item and notify
            await r.lrem(key, 1, raw)
            await _publish(f"✅ accepted {sid} — pushed {s['path']}")
            return {"status": "ok"}

    return {"status": "not-found"}


# ─── reject a suggestion ────────────────────────────────────────────────
@app.post("/suggestions/{sid}/reject", response_class=JSONResponse)
async def reject_suggestion(sid: str):
    for key in SUG_KEYS.values():
        for raw in await r.lrange(key, 0, -1):
            s = json.loads(raw)
            if s["id"] == sid:
                await r.lrem(key, 1, raw)
                await _publish(f"🛑 rejected {sid}")
                return {"status": "ok"}

    return {"status": "not-found"}
