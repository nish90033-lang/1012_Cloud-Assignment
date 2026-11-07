import json

import clean


def rec(i, text, reply):
    return {"id": i, "text": text, "teacher_raw": reply if isinstance(reply, str) else json.dumps(reply)}


GOOD = {"intent": "weather_query", "date": None, "time": None, "place": "london"}


def test_each_rejection_reason_is_counted_once():
    records = [
        rec("C1", "what is the weather in london", GOOD),                                   # kept
        rec("C2", "what is the weather in london", "```json\n{}\n```"),                     # (a) not JSON
        rec("C3", "what is the weather in london", {"intent": "weather_query"}),            # (b) keys
        rec("C4", "what is the weather in london", {**GOOD, "intent": "play_music"}),       # (c) intent
        rec("C5", "what is the weather in london", {**GOOD, "place": "paris"}),             # (d) slot not in text
        rec("C6", "what is the weather in london", GOOD),                                   # duplicate of C1
    ]
    kept, c = clean.clean(records)
    assert [r["id"] for r in kept] == ["C1"]
    got = [c[k] for k in ("a_invalid_json", "b_wrong_keys", "c_bad_intent", "d_bad_slot", "duplicates", "kept")]
    assert got == [1, 1, 1, 1, 1, 1]
    assert c["input"] == 6


def test_duplicate_keeps_smallest_id_and_output_is_id_ordered():
    records = [rec("C9", "set an alarm", {**GOOD, "intent": "alarm_set", "place": None}),
               rec("C2", "set an alarm", {**GOOD, "intent": "alarm_set", "place": None}),
               rec("C5", "remove it", {**GOOD, "intent": "calendar_remove", "place": None})]
    kept, c = clean.clean(records)
    assert [r["id"] for r in kept] == ["C2", "C5"]
    assert c["duplicates"] == 1


def test_slot_must_be_null_or_string_in_command_case_insensitive():
    assert clean.classify(rec("C1", "Weather in London", {**GOOD, "place": "london"})) is None
    assert clean.classify(rec("C1", "weather", {**GOOD, "place": 5})) == "d"
    assert clean.classify(rec("C1", "weather", [1, 2])) == "b"


def test_checksum_is_reproducible():
    import hashlib
    kept, _ = clean.clean([rec("C1", "what is the weather in london", GOOD)])
    assert hashlib.sha256(clean.serialise(kept)).hexdigest() == hashlib.sha256(clean.serialise(list(kept))).hexdigest()
