# orchestrator/support_worker.py
"""
Background worker:
  1. Pops a job JSON from Redis   queue:SupportAgent
  2. Sends it to the OpenAI chat‑completions endpoint (tools = function schema)
  3. Hands the function‑call off to Runner so the real Python tool runs
  4. Publishes every step to Redis pub/sub  logs:SupportAgent
"""

from __future__ import annotations
import os, json, asyncio, traceback, inspect
from typing import Any, Dict

from redis.asyncio import Redis

from orchestrator.agents.support_agent import support_agent            # tools+schema
from orchestrator.agents.run         import Runner
from orchestrator.agents.openai_agents import oa                        # ↖ client helper

# ─── Redis ─────────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis = Redis.from_url(REDIS_URL, decode_responses=True)

QUEUE = "queue:SupportAgent"
LOG   = "logs:SupportAgent"

# ─── OpenAI client (uses SUPPORT_AGENT_API_KEY) ────────────────────────
client = oa("SUPPORT_AGENT_API_KEY")     # returns an `OpenAI` client

# helper: push a line into Live‑log
async def log(event: Dict[str, Any]) -> None:
    await redis.publish(LOG, json.dumps(event))

# ─── main loop ─────────────────────────────────────────────────────────
async def main() -> None:
    print("SupportAgent worker booted", flush=True)

    while True:
        raw = await redis.rpop(QUEUE)
        if not raw:
            await asyncio.sleep(1)
            continue

        job   = json.loads(raw)
        utext = job.get("input", "")

        # 1️⃣  user message → log
        await log({"type":"message",
                   "data": json.dumps({"role":"user","content":utext})})

        try:
            # 2️⃣  call OpenAI ­– ask model to pick exactly one function
            resp = client.chat.completions.create(
                model       = support_agent.model,
                messages    = [
                    {"role":"system",     "content": support_agent.instructions},
                    {"role":"user",       "content": utext},
                ],
                tools       = support_agent.functions,
                tool_choice = "auto",
            )

            assistant_msg = resp.choices[0].message

            # assistant reply → log
            await log({"type":"message",
                       "data": json.dumps({"assistant": assistant_msg.dict()})})

            if not assistant_msg.tool_calls:
                await log({"type":"message",
                           "data": json.dumps({"error":"assistant did not call a tool"})})
                continue

            call   = assistant_msg.tool_calls[0]
            name   = call.function.name
            args   = json.loads(call.function.arguments)

            # function‑call → log
            await log({"type":"message",
                       "data": json.dumps({"function_call":{"name":name,
                                                            "arguments":args}})})

            # 3️⃣  hand off to Runner (runs the actual Python function)
            result = await Runner.run(support_agent, input={"name":name,"args":args})

            # 4️⃣  tool result → log
            await log({"type":"message",
                       "data": json.dumps({"tool_result": result["final_output"]})})

        except Exception as e:
            tb = traceback.format_exc()
            print("‼️  OpenAI/tool failure:", tb, flush=True)
            await log({"type":"message",
                       "data": json.dumps({"error": str(e)})})

if __name__ == "__main__":
    asyncio.run(main())
