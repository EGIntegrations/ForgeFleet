# orchestrator/agents/run.py
"""
Local **Runner** that maps {"name": "<tool>", "args": {...}}
to an actual callable on the Agent instance.
The runner always returns a dict so callers do not break.
"""

from __future__ import annotations

import asyncio
from typing import Callable, List

# ---------------- Minimal local Agent helper ----------------
class Agent:  # still handy for very-simple local agents
    def __init__(self, name: str, instructions: str, tools: List[Callable]):
        self.name = name
        self.instructions = instructions
        self.tools = tools
        for t in tools:
            setattr(self, t.__name__, t)

def function_tool(fn):
    fn.name = fn.__name__
    return fn

# ---------------- Optional span (future tracing) -------------
class SpanData:
    def __init__(self):
        self.tools: List[str] = []

class Span:
    def __init__(self):
        self.span_data = SpanData()

# ---------------- Runner -------------------------------------
class Runner:
    @staticmethod
    async def run(agent, input: dict) -> dict:
        current_span = Span()

        all_tools: List[Callable] = getattr(agent, "tools", [])
        current_span.span_data.tools = [
            getattr(tool, "name", tool.__name__) for tool in all_tools
        ]

        tool_name = input.get("name")
        tool_args = input.get("args", {})

        if not tool_name:  # assistant replied but didn’t call a tool
            return {"final_output": "Assistant did not call any tool."}

        for tool in all_tools:
            # fall back to __name__ if no .name
            tname = getattr(tool, "name", tool.__name__)
            if tname == tool_name:
                print(f"Executing tool={tname} args={tool_args}")
                # run sync tool in a thread
                result = await asyncio.to_thread(tool, **tool_args)
                return {"final_output": result}

        raise ValueError(f"No matching tool found for name: {tool_name}")
