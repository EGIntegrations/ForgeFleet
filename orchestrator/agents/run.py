# orchestrator/agents/run.py
import asyncio
from typing import List, Callable

# Corrected Agent and function_tool definitions
class Agent:
    def __init__(self, name, instructions, tools):
        self.name = name
        self.instructions = instructions
        self.tools = tools
        for tool in tools:
            setattr(self, tool.name, tool)

def function_tool(fn):
    fn.name = fn.__name__
    return fn

class SpanData:
    def __init__(self):
        self.tools = []

class Span:
    def __init__(self):
        self.span_data = SpanData()

class Runner:
    @staticmethod
    async def run(agent, input: dict):
        current_span = Span()

        # Dynamically gather all tools (functions) from the agent
        all_tools: List[Callable] = agent.tools

        # Set tool names properly
        current_span.span_data.tools = [tool.name for tool in all_tools]

        # Pick the matching tool by name from input
        tool_name = input.get("name")
        tool_args = input.get("args", {})

        for tool in all_tools:
            if tool.name == tool_name:
                print(f"Executing tool: {tool_name} with args: {tool_args}")
                result = await asyncio.to_thread(tool, **tool_args)
                return result

        raise ValueError(f"No matching tool found for name: {tool_name}")
