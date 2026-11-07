"""Teacher-labelling worker (Task 1).

Reads SHARD_INDEX and SHARD_COUNT. Takes the commands whose line number (from 0) satisfies
line % SHARD_COUNT == SHARD_INDEX, asks the teacher (Ollama, phi3.5, temperature 0, seed 42) and writes
{"id", "text", "teacher_raw"} lines to datasets/teacher/shard-<SHARD_INDEX>.jsonl.

The shard object is re-uploaded every CHECKPOINT_EVERY records and on exit, and a restarted worker resumes
from the object, so a crash after hours of CPU labelling does not lose work. teacher_raw is stored exactly as returned.
"""
import json
import os
import sys
import time

import requests
import s3util

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.k3d.internal:11434")
MODEL = os.environ.get("TEACHER_MODEL", "phi3.5")
PROMPT_FILE = os.environ.get("PROMPT_FILE", "/app/prompts/teacher_prompt.txt")
POOL_KEY = os.environ.get("POOL_KEY", "commands_pool.jsonl")
CHECKPOINT_EVERY = int(os.environ.get("CHECKPOINT_EVERY", "25"))
NUM_PREDICT = int(os.environ.get("NUM_PREDICT", "100"))


def shard_of(lines, index, count):
    """Return the (line_number, record) pairs belonging to shard `index` of `count`."""
    return [(n, rec) for n, rec in enumerate(lines) if n % count == index]


def build_prompt(template, command):
    # str.replace, not str.format: the template contains literal braces (JSON examples).
    return template.replace("{command}", command)


def ask_teacher(prompt):
    body = {"model": MODEL, "prompt": prompt, "stream": False,
            "options": {"temperature": 0, "seed": 42, "num_predict": NUM_PREDICT}}
    for attempt in range(5):
        try:
            r = requests.post(f"{OLLAMA_URL}/api/generate", json=body, timeout=600)
            r.raise_for_status()
            return r.json()["response"]
        except Exception as exc:  # network hiccup, Ollama busy or restarting
            print(f"teacher call failed ({exc}); retry {attempt + 1}/5", file=sys.stderr, flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("teacher unreachable")


def main():
    index = int(os.environ["SHARD_INDEX"])
    count = int(os.environ["SHARD_COUNT"])
    assert 0 <= index < count
    s3 = s3util.client()
    pool = [json.loads(x) for x in s3util.get_text(s3, "datasets", POOL_KEY).splitlines() if x.strip()]
    mine = shard_of(pool, index, count)
    out_key = f"teacher/shard-{index}.jsonl"
    done = {}
    if s3util.exists(s3, "datasets", out_key):
        for x in s3util.get_text(s3, "datasets", out_key).splitlines():
            if x.strip():
                rec = json.loads(x)
                done[rec["id"]] = rec
    template = open(PROMPT_FILE, encoding="utf-8").read().rstrip("\n")
    print(f"shard {index}/{count}: {len(mine)} commands, {len(done)} already done", flush=True)

    def flush():
        ordered = [done[r["id"]] for _, r in mine if r["id"] in done]
        s3util.put_text(s3, "datasets", out_key, "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in ordered))

    since = 0
    for _, rec in mine:
        if rec["id"] in done:
            continue
        raw = ask_teacher(build_prompt(template, rec["text"]))
        done[rec["id"]] = {"id": rec["id"], "text": rec["text"], "teacher_raw": raw}
        since += 1
        if since >= CHECKPOINT_EVERY:
            flush()
            since = 0
            print(f"shard {index}: {len(done)}/{len(mine)}", flush=True)
    flush()
    print(f"shard {index}: finished, {len(done)} records", flush=True)


if __name__ == "__main__":
    main()
