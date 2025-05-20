# orchestrator/agents/planner_agent.py

"""
PlannerAgent – breaks a project brief into agent-specific jobs.
Queues them to Redis, keeping your existing approval pipeline intact.
"""

from __future__ import annotations
import os, json, time, uuid, inspect
from typing import Any, Dict, List
from redis import Redis

from orchestrator.agents.openai_agents import AssistantAgent

# ——— config
VECTOR_ID = os.getenv("PLANNER_VECTOR_ID")
if not VECTOR_ID:
    raise RuntimeError("Set PLANNER_VECTOR_ID in .env")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_sync = Redis.from_url(REDIS_URL, decode_responses=True)

# helper: enqueue a job for another agent
def enqueue_job(agent: str, input: str, note: str = "", priority: str = "Medium", status: str = "Planned", depends_on: str = ""):
    """
    Place a JSON job dict onto queue:{agent}, with optional metadata.
    Also pushes a simplified summary into scope:{agent} for the UI.
    """
    job = {
        "cmd": "message",
        "input": input,
        "note": note or "AUTO_APPROVE: This job is ready",
        "meta": {
            "priority": priority,
            "status": status,
            "depends_on": depends_on
        }
    }
    # Main job for the agent
    redis_sync.lpush(f"queue:{agent}", json.dumps(job))

    # UI-friendly summary for project scope
    summary = {
        "task": input[:100],
        "priority": priority,
        "status": status,
        "depends_on": depends_on,
        "agent": agent,
        "timestamp": int(time.time())
    }
    redis_sync.lpush(f"scope:{agent}", json.dumps(summary))

    return f"✅ queued job for {agent}: <{note or input[:60]}>"

# enqueue *multiple* jobs in one call  # NEW
def enqueue_jobs(jobs: List[Dict[str, Any]]) -> str:
    """
    Accepts a list like:
      [
        {"agent":"GitAgent","input":"Create FastAPI skeleton", ...},
        {"agent":"SwiftAgent","input":"Pytest coverage", ...},
        ...
      ]
    Queues every job and returns a short confirmation.
    """
    # Accept both list and string (fix for LLM JSON output)
    if isinstance(jobs, str):
        jobs = json.loads(jobs)
    for j in jobs:
        enqueue_job(**j)
    return f"✅ queued {len(jobs)} jobs"

# convert Python tools → OpenAI function-call schema
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

TOOLS = [enqueue_job, enqueue_jobs]
FUNCTION_SCHEMAS = [to_schema(t) for t in TOOLS]

planner_agent = AssistantAgent(
    name = "PlannerAgent",
    model = "o4-mini-2025-04-16",  # use the premium model

    instructions = (
        "You are ForgeFleet’s high-level project planner.\n"
        "1. Ask clarifying questions UNTIL you fully understand the project requirements. If all needed details are present, skip questions and proceed.\n"
        "2. Once requirements are clear, DO NOT WAIT for further user input or say 'continue'.\n"
        "3. Immediately design the full project scope, architecture, folder structure, and deliverables.\n"
        "4. Break down the scope into concrete jobs. Assign backend/frontend/features to GitAgent, tests to SwiftAgent, docs/support to SupportAgent.\n"
        "5. ALWAYS spread jobs logically across ALL agents. Never assign everything to a single agent.\n"
        "6. Batch enqueue all jobs at once using enqueue_jobs([...]), or individually if needed. Include dependencies and metadata for each job.\n"
        "7. When all jobs have been enqueued and the project plan is fully complete, THEN (and only then) send a final message like 'Project planning complete! All jobs have been queued.'\n"
        "8. Do not wait for 'continue' or ask for permission after clarifying. Run end-to-end until the plan is finished and all jobs are queued.\n"
        "9. Use function calls (not plain text) for all job queuing. Only send text when planning is fully complete.\n"
  ),

    tools = TOOLS,
    functions = FUNCTION_SCHEMAS,
)
