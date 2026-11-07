"""Run the teacher (Ollama phi3.5, same prompt and settings as Task 1) over validation.jsonl for score.py."""
import argparse
import json
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))
from worker import build_prompt  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/validation.jsonl")
    ap.add_argument("--out", default="results/teacher_predictions.jsonl")
    ap.add_argument("--prompt", default="prompts/teacher_prompt.txt")
    ap.add_argument("--ollama", default=os.environ.get("OLLAMA_URL", "http://localhost:11434"))
    a = ap.parse_args()
    template = open(a.prompt, encoding="utf-8").read().rstrip("\n")
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    completed = set()
    if os.path.exists(a.out):
        with open(a.out, encoding="utf-8") as existing:
            for line in existing:
                if line.strip():
                    completed.add(json.loads(line)["id"])

    with open(a.data, encoding="utf-8") as f, open(a.out, "a", encoding="utf-8") as out:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r["id"] in completed:
                continue
            print(f"Evaluating {r['id']} ({len(completed)}/100 already completed)", flush=True)
            body = {"model": "phi3.5", "prompt": build_prompt(template, r["text"]), "stream": False,
                    "options": {"temperature": 0, "seed": 42, "num_predict": 100}}
            resp = requests.post(f"{a.ollama}/api/generate", json=body, timeout=1800)
            resp.raise_for_status()
            out.write(json.dumps({"id": r["id"], "prediction": resp.json()["response"]}) + "\n")
            out.flush()
            completed.add(r["id"])
    print(f"Total predictions: {len(completed)}")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
