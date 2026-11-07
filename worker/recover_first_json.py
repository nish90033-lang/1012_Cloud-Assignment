import glob
import hashlib
import json
import os
from collections import Counter

KEYS = {"intent", "date", "time", "place"}
INTENTS = {
    "alarm_set", "alarm_query", "calendar_set", "calendar_query",
    "calendar_remove", "weather_query", "datetime_query",
    "recommendation_events"
}

records = []
counts = Counter()

for path in sorted(glob.glob("results/raw_teacher/shard-*.jsonl")):
    with open(path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            counts["input"] += 1
            raw = str(rec.get("teacher_raw", ""))

            try:
                obj, end = json.JSONDecoder().raw_decode(raw.lstrip())
            except (ValueError, TypeError):
                counts["a_invalid_json"] += 1
                continue

            if not isinstance(obj, dict) or set(obj) != KEYS:
                counts["b_wrong_keys"] += 1
                continue

            if not isinstance(obj["intent"], str) or obj["intent"] not in INTENTS:
                counts["c_bad_intent"] += 1
                continue

            command = rec["text"].lower()
            bad = False
            for slot in ("date", "time", "place"):
                value = obj[slot]
                if value is not None and (
                    not isinstance(value, str) or value.lower() not in command
                ):
                    bad = True
                    break

            if bad:
                counts["d_bad_slot"] += 1
                continue

            cleaned = {
                "id": rec["id"],
                "text": rec["text"],
                "teacher_raw": json.dumps(obj, ensure_ascii=False)
            }
            records.append(cleaned)

records.sort(key=lambda r: r["id"])

seen = set()
kept = []
for rec in records:
    key = " ".join(rec["text"].split())
    if key in seen:
        counts["duplicates"] += 1
        continue
    seen.add(key)
    kept.append(rec)

counts["kept"] = len(kept)
assert counts["input"] == (
    counts["a_invalid_json"] + counts["b_wrong_keys"]
    + counts["c_bad_intent"] + counts["d_bad_slot"]
    + counts["duplicates"] + counts["kept"]
)

out = "results/recovered_v1"
os.makedirs(out, exist_ok=True)

data = "".join(
    json.dumps(r, ensure_ascii=False) + "\n" for r in kept
).encode("utf-8")

digest = hashlib.sha256(data).hexdigest()

with open(f"{out}/train.jsonl", "wb") as f:
    f.write(data)

with open(f"{out}/train.sha256", "w") as f:
    f.write(f"{digest}  train.jsonl\n")

with open(f"{out}/clean_counts.json", "w") as f:
    json.dump(dict(counts), f, indent=2)

print(json.dumps(dict(counts), indent=2))
print(f"SHA256: {digest}")
print(f"Dataset: {out}/train.jsonl")
