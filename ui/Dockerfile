FROM python:3.11-slim
WORKDIR /app
RUN pip install redis[async]
RUN pip install fastapi uvicorn[standard] jinja2
COPY . /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
