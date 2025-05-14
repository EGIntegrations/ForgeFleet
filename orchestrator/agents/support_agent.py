# orchestrator/agents/support_agent.py
"""
SupportAgent – queues every code/doc change for human approval.
Now uses a *synchronous* Redis handle inside suggest_change().
"""
from __future__ import annotations
import os, json, time, uuid, inspect
from typing import Any, Dict, List

# ── standard (sync) Redis for simple lpush ─────────────────────────────
from redis import Redis  # <‑‑ sync client

from orchestrator.tools.devtools import write_file, run_shell
from orchestrator.agents.openai_agents import AssistantAgent

# ───────────────────────────────────────────────────────────────────────
VECTOR_ID = os.getenv("SUPPORT_VECTOR_ID")
if not VECTOR_ID:
    raise RuntimeError("Set SUPPORT_VECTOR_ID in your .env")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_sync = Redis.from_url(REDIS_URL, decode_responses=True)   # sync handle
SUG_KEY    = "suggestions:SupportAgent"

# ── tool: queue a suggestion instead of writing immediately ────────────
def suggest_change(path: str, content: str, note: str = "") -> str:
    """Queue a file change for human review (dashboard ✓ / ✗)."""
    suggestion = {
        "id": str(uuid.uuid4()),
        "ts": int(time.time()),
        "agent": "SupportAgent",
        "path": path,
        "content": content,
        "note": note,
    }
    # newest‑first ordering
    redis_sync.lpush(SUG_KEY, json.dumps(suggestion))
    return f"💡 queued suggestion {suggestion['id']}"

# ── convert Python tools → JSON function‑call schema for GPT‑4o‑beta ──
def to_schema(fn) -> Dict[str, Any]:
    sig = inspect.signature(fn)
    props, req = {}, []
    for name, param in sig.parameters.items():
        props[name] = {"type": "string"}
        if param.default is inspect._empty:
            req.append(name)
    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": (fn.__doc__ or fn.__name__).strip(),
            "parameters": {
                "type": "object",
                "properties": props,
                "required": req,
            },
        },
    }

# ── expose tools & function schemas to the model ───────────────────────
TOOLS            = [suggest_change]
FUNCTION_SCHEMAS = [to_schema(t) for t in TOOLS]

support_agent = AssistantAgent(
    name         = "SupportAgent",
    model        = "gpt-4o-mini",
    instructions = (
        "You are a ForgeFleet support assistant.\n"
        "ALWAYS respond with **exactly one** function call.\n"
        "If you want to propose a code/document change, call suggest_change()."
    ),
    tools        = TOOLS,
    functions    = FUNCTION_SCHEMAS,
)
