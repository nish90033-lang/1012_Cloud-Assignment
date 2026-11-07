"""Command-parser inference service (Task 3).

Configuration (environment): MODEL_URI (s3://bucket/prefix/), MODEL_VERSION, S3_ENDPOINT, MAX_NEW_TOKENS, FAULT_INJECT.
S3 credentials (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY) come from a Kubernetes Secret; the Pod name from the downward API.
"""
import json
import os
import tempfile
import threading
from urllib.parse import urlparse

import inference
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

MODEL_URI = os.environ.get("MODEL_URI", "s3://models/v1/")
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "64"))
POD_NAME = os.environ.get("POD_NAME") or os.environ.get("HOSTNAME", "unknown")

app = FastAPI(title="command-parser")
state = {"model": None, "tokenizer": None, "ready": False, "error": None}
_lock = threading.Lock()  # one generation at a time: the container has a single CPU core
_schema = None


class ParseRequest(BaseModel):
    text: str


def download_model(uri, endpoint, dest):
    """Download every object under s3://bucket/prefix/ into dest (model + tokenizer files)."""
    import boto3
    from botocore.config import Config

    u = urlparse(uri)
    bucket, prefix = u.netloc, u.path.lstrip("/")
    s3 = boto3.client(
        "s3", endpoint_url=endpoint,
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}, retries={"max_attempts": 5}),
    )
    n = 0
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            name = obj["Key"][len(prefix):]
            if not name or name.endswith("/") or name.endswith(".sha256"):
                continue
            target = os.path.join(dest, name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            s3.download_file(bucket, obj["Key"], target)
            n += 1
    if n == 0:
        raise RuntimeError(f"no objects found under {uri}")
    print(f"downloaded {n} files from {uri} to {dest}", flush=True)


def load_in_background():
    try:
        d = tempfile.mkdtemp(prefix="model-")
        download_model(MODEL_URI, S3_ENDPOINT, d)
        state["model"], state["tokenizer"] = inference.load_model(d)
        state["ready"] = True
        print(f"model {MODEL_VERSION} loaded", flush=True)
    except Exception as exc:  # stay alive (healthz 200) but never become ready
        state["error"] = str(exc)
        print(f"model load failed: {exc}", flush=True)


@app.on_event("startup")
def _startup():
    global _schema
    _schema = inference.load_schema()
    if os.environ.get("SKIP_MODEL_LOAD") != "1":
        threading.Thread(target=load_in_background, daemon=True).start()


def _headers():
    return {"X-Model-Version": MODEL_VERSION, "X-Served-By": POD_NAME}


@app.get("/healthz")
def healthz():
    return {"status": "alive"}


@app.get("/readyz")
def readyz():
    if state["ready"]:
        return {"status": "ready"}
    return JSONResponse({"status": "loading"}, status_code=503)


def run_model(text):
    with _lock:
        return inference.generate(state["model"], state["tokenizer"], text, MAX_NEW_TOKENS)


@app.post("/parse")
def parse(req: ParseRequest):
    if not state["ready"]:
        return JSONResponse({"error": "model_not_ready"}, status_code=503, headers=_headers())
    raw = run_model(req.text)
    if os.environ.get("FAULT_INJECT") == "1":
        raw = "not json"
    obj = inference.validate_output(raw, _schema)
    if obj is None:
        return JSONResponse({"error": "invalid_model_output"}, status_code=500, headers=_headers())
    return Response(content=json.dumps(obj), media_type="application/json", headers=_headers())
