FROM python:3.11-slim

# ---- system deps ----------------------------------------------------
RUN apt-get update \
 && apt-get install -y git \
 && apt-get install -y --no-install-recommends build-essential gcc \
 && rm -rf /var/lib/apt/lists/*

# ---- python deps ----------------------------------------------------
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- source code ----------------------------------------------------
COPY . /app

ENV PYTHONUNBUFFERED=true PYTHONDONTWRITEBYTECODE=true
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
