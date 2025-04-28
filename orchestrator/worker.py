import asyncio, json, os
from redis.asyncio import Redis

# --- local imports *inside* the orchestrator package -------------
from orchestrator.agents               import Agent, Runner, function_tool
from orchestrator.tools.devtools       import write_file, run_shell
# -----------------------------------------------------------------

# make sure every tool exposes a .name for `agents.run`
write_file.name = "write_file"
run_shell.name  = "run_shell"

@function_tool
def echo(text: str) -> str:           # a trivial tool so you have three
    return text
echo.name = "echo"

demo_agent = Agent(
    name         = "DemoAgent",
    instructions = "Use write_file or run_shell when appropriate.",
    tools        = [echo, write_file, run_shell],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis     = Redis.from_url(REDIS_URL)

QUEUE = "queue:DemoAgent"
LOG   = "logs:DemoAgent"

async def main() -> None:
    print("DemoAgent worker booted", flush=True)
    while True:
        raw = await redis.rpop(QUEUE)
        if raw:
            message = json.loads(raw)
            await redis.publish(LOG, f"INPUT ▶ {message}")
            result  = await Runner.run(demo_agent, input=message)
            await redis.publish(LOG, f"OUTPUT ▶ {result.final_output}")
        else:
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
