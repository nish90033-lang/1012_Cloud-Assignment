"""Run a local model directory (or the untrained base model) over a labelled file and write predictions for score.py.

    python evaluate/run_student.py --model artifacts/v1 --data data/validation.jsonl --out results/student_v1_predictions.jsonl
    python evaluate/run_student.py --model EleutherAI/pythia-70m ...      # the untrained baseline
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service"))
import inference  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", default="data/validation.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-new-tokens", type=int, default=64)
    a = ap.parse_args()
    model, tok = inference.load_model(a.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.data, encoding="utf-8") as f, open(a.out, "w", encoding="utf-8") as out:
        for line in f:
            if line.strip():
                r = json.loads(line)
                pred = inference.generate(model, tok, r["text"], a.max_new_tokens)
                out.write(json.dumps({"id": r["id"], "prediction": pred}) + "\n")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
