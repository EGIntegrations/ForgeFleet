# orchestrator/agents/setup_planner_agent.py

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("PLANNER_AGENT_API_KEY"))

vector_store = client.vector_stores.create(name="PlannerAgentStore")

print("✅ PLANNER_VECTOR_ID =", vector_store.id)
