FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential gcc g++ git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Poetry files first
COPY pyproject.toml poetry.lock* ./

RUN pip install --no-cache-dir poetry \
 && poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root

# Now copy your source code
COPY . /app/orchestrator

ENV PYTHONPATH=/app

CMD ["python", "-m", "orchestrator.worker"]
