# orchestrator/support_worker.py (SwiftAgent worker)

from __future__ import annotations
import os, json, asyncio, traceback, inspect
from typing import Any, Dict

from redis.asyncio import Redis
from orchestrator.agents.swift_agent import swift_agent
from orchestrator.agents.run import Runner
from orchestrator.agents.openai_agents import oa

# ─── Redis ─────────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis = Redis.from_url(REDIS_URL, decode_responses=True)

QUEUE = "queue:SwiftAgent"
LOG   = "logs:SwiftAgent"

# ─── OpenAI client (uses SWIFT_AGENT_API_KEY) ────────────────────────
client = oa("SWIFT_AGENT_API_KEY")  # returns an `OpenAI` client

# helper: push a line into Live‑log
async def log(event: Dict[str, Any]) -> None:
    await redis.publish(LOG, json.dumps(event))

# ─── main loop ─────────────────────────────────────────────────────────
async def main() -> None:
    print("SwiftAgent worker booted", flush=True)

    while True:
        raw = await redis.rpop(QUEUE)
        if not raw:
            await asyncio.sleep(1)
            continue

        job = json.loads(raw)
        utext = job.get("input", "")

        # 1️⃣  user message → log
        await log({"type": "message",
                   "data": json.dumps({"role": "user", "content": utext})})

        try:
            # 2️⃣  call OpenAI ­– ask model to pick a function
            resp = client.chat.completions.create(
                model=swift_agent.model,
                messages=[
                    {"role": "system", "content": swift_agent.instructions},
                    {"role": "user", "content": utext},
                ],
                tools=swift_agent.functions,
                tool_choice="auto",
            )

            assistant_msg = resp.choices[0].message

            # assistant reply → log
            await log({"type": "message",
                       "data": json.dumps({"assistant": assistant_msg.dict()})})

            if not assistant_msg.tool_calls:
                await log({"type": "message",
                           "data": json.dumps({"error": "assistant did not call a tool"})})
                continue

            call = assistant_msg.tool_calls[0]
            name = call.function.name
            args = json.loads(call.function.arguments)

            # 3️⃣  function‑call → log
            await log({"type": "message",
                       "data": json.dumps({"function_call": {"name": name, "arguments": args}})})

            # 4️⃣  hand off to Runner
            result = await Runner.run(swift_agent, input={"name": name, "args": args})

            # 5️⃣  tool result → log
            await log({"type": "message",
                       "data": json.dumps({"tool_result": result["final_output"]})})

            # 6️⃣  queue suggestion to Redis (for UI)
            if "path" in result and "content" in result and "note" in result:
                suggestion = {
                    "id": result.get("id", os.urandom(8).hex()),
                    "agent": "SwiftAgent",
                    "path": result["path"],
                    "content": result["content"],
                    "note": result["note"]
                }
                await redis.lpush("suggestions:SwiftAgent", json.dumps(suggestion))

        except Exception as e:
            tb = traceback.format_exc()
            print("‼️  OpenAI/tool failure:", tb, flush=True)
            await log({"type": "message",
                       "data": json.dumps({"error": str(e)})})

if __name__ == "__main__":
    asyncio.run(main())
