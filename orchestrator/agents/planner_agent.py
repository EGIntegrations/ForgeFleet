# orchestrator/agents/planner_agent.py
"""
PlannerAgent – breaks a project brief into agent‑specific jobs.
Queues them to Redis, keeping your existing approval pipeline intact.
"""
from __future__ import annotations
import os, json, time, uuid, inspect
from typing import Any, Dict, List
from redis import Redis

from orchestrator.agents.openai_agents import AssistantAgent

# ── config ─────────────────────────────────────────────────────────────
VECTOR_ID = os.getenv("PLANNER_VECTOR_ID")
if not VECTOR_ID:
    raise RuntimeError("Set PLANNER_VECTOR_ID in .env")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_sync = Redis.from_url(REDIS_URL, decode_responses=True)

# helper: enqueue a job for another agent
def enqueue_job(agent: str, input: str, note: str = "") -> str:
    """
    Place a JSON job dict onto queue:{agent}.
    Returns confirmation text for the LLM.
    """
    job = {"cmd": "message", "input": input, "note": note}
    redis_sync.lpush(f"queue:{agent}", json.dumps(job))
    return f"📮 queued job for {agent}: «{note or input[:60]}…»"

# convert Python tools → OpenAI function‑call schema
def to_schema(fn) -> Dict[str, Any]:
    sig, props, req = inspect.signature(fn), {}, []
    for name, prm in sig.parameters.items():
        props[name] = {"type": "string"}
        if prm.default is inspect._empty:
            req.append(name)
    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": (fn.__doc__ or fn.__name__).strip(),
            "parameters": {"type": "object", "properties": props, "required": req},
        },
    }

TOOLS            = [enqueue_job]
FUNCTION_SCHEMAS = [to_schema(t) for t in TOOLS]

planner_agent = AssistantAgent(
    name         = "PlannerAgent",
    model        = "o4-mini-2025-04-16",          # use the premium model
    instructions = (
        "You are ForgeFleet’s high‑level project planner.\n"
        "1. Ask the user clarifying questions until you fully understand the project.\n"
        "2. Design the architecture, tech‑stack and deliverables.\n"
        "3. Break the work into concrete jobs and call enqueue_job(agent, input, note).\n"
        "4. Use GitAgent for code creation/refactor, SwiftAgent for tests/perf, "
        "SupportAgent for docs/help, DemoAgent for demos.\n"
        "ALWAYS respond with exactly one function call."
    ),
    tools        = TOOLS,
    functions    = FUNCTION_SCHEMAS,
)
