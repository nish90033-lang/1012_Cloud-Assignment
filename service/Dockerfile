# Build from the repository root:  docker build -f service/Dockerfile -t cmdparser:1.0 .
# CPU-only PyTorch wheel (no CUDA libraries) keeps the image well under 2 GB. No model weights are copied in:
# the model is downloaded from object storage at start-up.
FROM python:3.11.9-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HUB_OFFLINE=1
WORKDIR /app
COPY service/requirements.txt .
RUN pip install -r requirements.txt
COPY service/app.py service/inference.py ./
COPY data/schema.json ./schema.json
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
