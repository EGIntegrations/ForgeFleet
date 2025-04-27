from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
import os, redis.asyncio as aioredis, json, uuid

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = aioredis.from_url(REDIS_URL)
env = Environment(loader=FileSystemLoader("templates"))

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def index():
    # fetch live container stats (placeholder for now)
    template = env.get_template("index.html")
    html = template.render()
    return HTMLResponse(html)

# WebSocket for real-time logs
@app.websocket("/ws/{agent}")
async def ws_logs(ws: WebSocket, agent: str):
    await ws.accept()
    pubsub = r.pubsub()
    await pubsub.subscribe(f"logs:{agent}")
    try:
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                await ws.send_text(msg["data"].decode())
    except WebSocketDisconnect:
        await pubsub.unsubscribe(f"logs:{agent}")

@app.get("/agents", response_class=HTMLResponse)
async def agents_partial():
    # For now we hard-code DemoAgent; later query Redis keys
    queue_len = await r.llen("queue:DemoAgent")
    row = f"""
    <tr>
      <td>DemoAgent</td>
      <td style='color:lime'>ONLINE</td>
      <td>{queue_len}</td>
      <td><button onclick="openLog('DemoAgent')">Open</button></td>
    </tr>
    """
    return HTMLResponse(row)
