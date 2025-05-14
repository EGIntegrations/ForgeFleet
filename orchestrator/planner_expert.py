# orchestrator/planner_expert.py  (independent worker process)
from __future__ import annotations
import os, json, asyncio, traceback
from redis.asyncio import Redis
from orchestrator.agents.planner_agent import planner_agent
from orchestrator.agents.openai_agents import oa           # existing helper
from orchestrator.agents.run import Runner                 # existing helper

REDIS_URL  = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis      = Redis.from_url(REDIS_URL, decode_responses=True)

QUEUE      = "queue:PlannerAgent"
LOG        = "logs:PlannerAgent"

client = oa("PLANNER_AGENT_API_KEY")

async def log(event):
    await redis.publish(LOG, json.dumps(event))

async def main():
    print("PlannerAgent worker booted", flush=True)
    while True:
        raw = await redis.rpop(QUEUE)
        if not raw:
            await asyncio.sleep(1)
            continue

        job = json.loads(raw)
        utext = job.get("input", "")

        await log({"type": "message",
                   "data": json.dumps({"role": "user", "content": utext})})

        try:
            resp = client.chat.completions.create(
                model   = planner_agent.model,
                messages=[{"role":"system","content": planner_agent.instructions},
                          {"role":"user"  ,"content": utext}],
                tools      = planner_agent.functions,
                tool_choice= "auto",
            )
            msg  = resp.choices[0].message
            await log({"type":"message",
                       "data": json.dumps({"assistant": msg.dict()})})

            if not msg.tool_calls:
                await log({"type":"message",
                           "data": json.dumps({"error":"no function call"})})
                continue

            call = msg.tool_calls[0]
            result = await Runner.run(planner_agent,
                                      input={"name": call.function.name,
                                             "args": json.loads(call.function.arguments)})
            await log({"type":"message",
                       "data": json.dumps({"tool_result": result["final_output"]})})

        except Exception as e:
            tb = traceback.format_exc()
            print("‼️ Planner fail:\n", tb, flush=True)
            await log({"type":"message",
                       "data": json.dumps({"error": str(e)})})

if __name__ == "__main__":
    asyncio.run(main())
