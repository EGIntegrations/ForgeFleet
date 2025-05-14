# orchestrator/agents/openai_agents.py
"""
Tiny helper layer so the local Runner can treat an OpenAI‑assistant
like any other agent that has .tools (Python callables) and .functions
(JSON‑schema definitions to send to the Chat Completions API).
"""

from __future__ import annotations
import os
from typing import Any, Dict, List, Callable

from openai import OpenAI


class AssistantAgent:
    """
    Minimal adapter – does **nothing** itself, just stores the metadata
    so other parts (support_worker / Runner) can read it.
    """

    def __init__(
        self,
        *,
        name: str,
        model: str,
        instructions: str,
        tools: List[Callable],
        functions: List[Dict[str, Any]] | None = None,
    ) -> None:
        self.name         = name
        self.model        = model
        self.instructions = instructions
        self.tools        = tools or []
        self.functions    = functions or []

        # expose each Python tool as attribute (Runner uses getattr)
        for t in self.tools:
            setattr(self, t.__name__, t)

    # handy when we need a plain dict
    def as_dict(self) -> Dict[str, Any]:
        return {
            "name":         self.name,
            "model":        self.model,
            "instructions": self.instructions,
            "functions":    self.functions,
        }


# ---------------------------------------------------------------------
# Helper: create an authenticated OpenAI client with *per‑agent* key
# ---------------------------------------------------------------------
def oa(env_var: str | None = None) -> OpenAI:
    """
    Return an OpenAI() client using the API‑key stored in the given
    environment variable (falls back to OPENAI_API_KEY).
    """
    key_name = env_var or "OPENAI_API_KEY"
    api_key  = os.getenv(key_name)
    if not api_key:
        raise RuntimeError(f"Set {key_name} in your environment (.env)")
    return OpenAI(api_key=api_key)
