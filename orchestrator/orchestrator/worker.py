import asyncio, os, logging
from openai_agents import AgentRuntime, Agent
from redis.asyncio import Redis

logging.basicConfig(level=logging.INFO)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis = Redis.from_url(REDIS_URL)

# --- example tool (stub) -----------------
async def echo_tool(text: str) -> str:
    return text

# --- simple agent ------------------------
demo_agent = Agent(
    name="DemoAgent",
    model="gpt-4o-mini",
    system_prompt="You are a helpful demo agent; use the echo tool.",
    tools=[echo_tool],
)

async def main():
    rt = AgentRuntime(redis=redis)
    rt.register(demo_agent)
    await rt.run()

if __name__ == "__main__":
    asyncio.run(main())
