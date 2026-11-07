"""Clean the teacher shards into datasets/v1/train.jsonl (+ train.sha256).  Task 1, step 6.

Usage:
  python worker/clean.py                      # reads shards from the datasets bucket, writes v1/ back to it
  python worker/clean.py --local-in DIR --local-out DIR   # same logic on local files (tests, offline use)

Rejection reasons are applied to each record in this order and a record is counted under the FIRST reason that applies:
  (a) reply is not valid JSON
  (b) not a JSON object with exactly the keys intent, date, time, place
  (c) intent not one of the eight
  (d) a slot is neither null nor a string that appears in the command (case-insensitive substring)
Then duplicates: among the records that passed (a)-(d), commands with the same text are collapsed and the one with the
smallest id is kept. Output is in id order, so the result is deterministic and train.sha256 is reproducible.
"""
import argparse
import glob
import hashlib
import json
import os

KEYS = {"intent", "date", "time", "place"}
INTENTS = {"alarm_set", "alarm_query", "calendar_set", "calendar_query", "calendar_remove",
           "weather_query", "datetime_query", "recommendation_events"}


def classify(rec):
    """Return None if the record is good, else 'a'|'b'|'c'|'d'."""
    try:
        obj = json.loads(str(rec.get("teacher_raw", "")).strip())
    except (ValueError, TypeError):
        return "a"
    if not isinstance(obj, dict) or set(obj.keys()) != KEYS:
        return "b"
    if obj["intent"] not in INTENTS:  # unhashable values (lists, dicts) also fail here
        return "c"
    text = rec["text"].lower()
    for slot in ("date", "time", "place"):
        v = obj[slot]
        if v is None:
            continue
        if not isinstance(v, str) or v.lower() not in text:
            return "d"
    return None


def clean(records):
    counts = {"input": len(records), "a_invalid_json": 0, "b_wrong_keys": 0, "c_bad_intent": 0,
              "d_bad_slot": 0, "duplicates": 0, "kept": 0}
    names = {"a": "a_invalid_json", "b": "b_wrong_keys", "c": "c_bad_intent", "d": "d_bad_slot"}
    good = []
    for rec in records:
        reason = classify(rec)
        if reason:
            counts[names[reason]] += 1
        else:
            good.append(rec)
    good.sort(key=lambda r: r["id"])
    seen, kept = set(), []
    for rec in good:
        key = " ".join(rec["text"].split())
        if key in seen:
            counts["duplicates"] += 1
            continue
        seen.add(key)
        kept.append(rec)
    counts["kept"] = len(kept)
    assert counts["input"] == sum(counts[k] for k in list(names.values()) + ["duplicates", "kept"])
    return kept, counts


def serialise(kept):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept).encode("utf-8")


def parse_lines(text):
    return [json.loads(x) for x in text.splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-in")
    ap.add_argument("--local-out")
    ap.add_argument("--counts-out", default="results/clean_counts.json")
    a = ap.parse_args()

    records = []
    if a.local_in:
        for p in sorted(glob.glob(os.path.join(a.local_in, "shard-*.jsonl"))):
            records += parse_lines(open(p, encoding="utf-8").read())
    else:
        import s3util
        s3 = s3util.client()
        pages = s3.get_paginator("list_objects_v2").paginate(Bucket="datasets", Prefix="teacher/shard-")
        keys = sorted(o["Key"] for page in pages for o in page.get("Contents", []))
        for k in keys:
            records += parse_lines(s3util.get_text(s3, "datasets", k))

    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids)), "an id appears in more than one shard output"
    kept, counts = clean(records)
    data = serialise(kept)
    digest = hashlib.sha256(data).hexdigest()
    sha_line = f"{digest}  train.jsonl\n"

    if a.local_out:
        os.makedirs(a.local_out, exist_ok=True)
        open(os.path.join(a.local_out, "train.jsonl"), "wb").write(data)
        open(os.path.join(a.local_out, "train.sha256"), "w").write(sha_line)
    else:
        s3.put_object(Bucket="datasets", Key="v1/train.jsonl", Body=data)
        s3.put_object(Bucket="datasets", Key="v1/train.sha256", Body=sha_line.encode())
    os.makedirs(os.path.dirname(a.counts_out) or ".", exist_ok=True)
    json.dump(counts, open(a.counts_out, "w"), indent=2)
    print(json.dumps(counts, indent=2))
    print(sha_line, end="")


if __name__ == "__main__":
    main()
