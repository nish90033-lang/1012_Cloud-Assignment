"""Prompt format, generation and output validation shared by the service, the evaluation scripts and the tests."""
import json
import os

import jsonschema

SCHEMA_PATH = os.environ.get("SCHEMA_PATH") or next(
    (p for p in ("/app/schema.json", os.path.join(os.path.dirname(__file__), "..", "data", "schema.json")) if os.path.exists(p)),
    "/app/schema.json",
)


def build_prompt(command):
    # Must be identical to the training format (training/train.py): "Command: <cmd>\nJSON: <reply>"
    return f"Command: {command}\nJSON:"


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)["json_schema"]


def validate_output(text, schema):
    """Return the parsed object if `text` is exactly one valid 4-key JSON object, else None."""
    try:
        obj = json.loads(text.strip())
        jsonschema.validate(obj, schema)
    except (ValueError, jsonschema.ValidationError):
        return None
    return obj


def generate(model, tokenizer, command, max_new_tokens):
    """Greedy decoding of the JSON reply for one command. Returns the raw generated text."""
    import torch

    inputs = tokenizer(build_prompt(command), return_tensors="pt")
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
        )
    text = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return text.split("\n")[0].strip()  # the reply is a single line; ignore anything after it


def load_model(path):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(1)  # the container is limited to 1 CPU core
    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.float32)
    model.eval()
    return model, tokenizer
