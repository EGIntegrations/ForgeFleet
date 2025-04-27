import asyncio, json, os
from redis.asyncio import Redis
from agents import Agent, Runner, function_tool
from tools.devtools import write_file, run_shell

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis = Redis.from_url(REDIS_URL)

# ---- simple echo tool ---------------------
@function_tool
def echo(text: str) -> str:
    return text

demo_agent = Agent(
    name="DemoAgent",
    instructions="Use write_file or run_shell when appropriate.",
    tools=[echo, write_file, run_shell],
)

QUEUE = "queue:DemoAgent"
LOG   = "logs:DemoAgent"

async def main() -> None:
    print("DemoAgent worker booted")
    while True:
        task = await redis.rpop(QUEUE)
        if task:
            message = task.decode()
            print("INPUT  ▶", message, flush=True)
            await redis.publish(LOG, f"INPUT  ▶ {message}")
            result = await Runner.run(demo_agent, input=message)
            print("OUTPUT ▶", result.final_output, flush=True)
            await redis.publish(LOG, f"OUTPUT ▶ {result.final_output}")
        else:
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
