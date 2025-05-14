import os
from openai import OpenAI

# ── 0.  Init client with Support-Agent key ────────────────────────────────────
client = OpenAI(api_key=os.getenv("GIT_AGENT_API_KEY"))

# ── 1.  Create the vector-store ───────────────────────────────────────────────
vector_store = client.vector_stores.create(name="Support Knowledge")

# ── 2.  Upload docs  → collect file-IDs ───────────────────────────────────────
file_paths = [
    "docs/git_guide.txt",
    "docs/api_reference.txt",
]
file_ids = []
for path in file_paths:
    with open(path, "rb") as f:
        up = client.files.create(file=f, purpose="assistants")
        file_ids.append(up.id)

# ── 3.  Attach those files to the store ───────────────────────────────────────
client.vector_stores.file_batches.create_and_poll(
    vector_store_id=vector_store.id,
    file_ids=file_ids,
)

# ── 4.  Create the Assistant (note the β namespace) ───────────────────────────
assistant = client.beta.assistants.create(
    name="GitAgent",
    instructions=(
        "You are a helpful assistant trained to provide guidance, create, and review  "
        "anything related to the Git  coding language and Github system, all syntax and guidance you'll need is located in swift_guide.txt."
    ),
    model="gpt-4.1-nano-2025-04-14",
    tools=[{"type": "file_search"}],
    tool_resources={
        "file_search": {"vector_store_ids": [vector_store.id]}
    },
)

# ── 5.  Display IDs for wiring into your worker ───────────────────────────────
print("✅ Assistant ID :", assistant.id)
print("📚 VectorStore  :", vector_store.id)
