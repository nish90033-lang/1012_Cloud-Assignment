# Build from the repository root: docker build -f worker/Dockerfile -t cmdparser-worker:1.0 .
FROM python:3.11.9-slim
WORKDIR /app
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker/ /app/worker/
COPY prompts/ /app/prompts/
WORKDIR /app/worker
CMD ["python", "worker.py"]
