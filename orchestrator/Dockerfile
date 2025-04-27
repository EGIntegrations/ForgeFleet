# orchestrator/Dockerfile
FROM python:3.11-slim

# ---------- deps ----------
WORKDIR /app
# copy Poetry files first to leverage Docker layer-cache
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# ---------- source code ----------
# copy the actual packages *after* deps are installed
COPY devtools_pb2*.py /app/
COPY orchestrator /app/orchestrator
COPY tools        /app/tools

# make 'tools' importable
ENV PYTHONPATH=/app

CMD ["python", "-m", "orchestrator.worker"]
