"""Sequence-level distillation: fine-tune Pythia-70M on the teacher's replies (Task 2). CPU only.

    python training/train.py --config training/config.yaml [--subset 50]

Example format:   Command: <command>\nJSON: <teacher reply><eos>
"""
import argparse
import csv
import hashlib
import json
import os
import random
import tarfile

import yaml


def load_examples(path, limit):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    rows.sort(key=lambda r: r["id"])  # train.jsonl is already in id order; be explicit
    return rows[:limit]


def build_example(tok, command, reply, max_len, mask_prompt):
    prompt_ids = tok(f"Command: {command}\nJSON:")["input_ids"]
    reply_ids = tok(" " + reply.strip())["input_ids"] + [tok.eos_token_id]
    ids = (prompt_ids + reply_ids)[:max_len]
    labels = ([-100] * len(prompt_ids) + reply_ids)[:max_len] if mask_prompt else list(ids)
    return ids, labels


def collate(batch, pad_id):
    n = max(len(i) for i, _ in batch)
    ids = [i + [pad_id] * (n - len(i)) for i, _ in batch]
    labels = [lab + [-100] * (n - len(lab)) for _, lab in batch]
    attn = [[1] * len(i) + [0] * (n - len(i)) for i, _ in batch]
    return ids, labels, attn


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="training/config.yaml")
    ap.add_argument("--subset", type=int, default=0, help="train on the first N records only (smoke test)")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config, encoding="utf-8"))

    import numpy as np
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    seed = cfg["seed"]
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    print(f"torch {torch.__version__}  transformers {transformers.__version__}  numpy {np.__version__}  seed {seed}")

    limit = a.subset if a.subset else cfg["max_records"]
    rows = load_examples(cfg["train_file"], limit)
    print(f"training on {len(rows)} records")

    tok = AutoTokenizer.from_pretrained(cfg["model_name"])
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(cfg["model_name"])
    model.train()
    data = [build_example(tok, r["text"], r["teacher_raw"], cfg["max_seq_length"], cfg["mask_prompt_loss"]) for r in rows]

    opt = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"])
    bs, epochs = cfg["batch_size"], cfg["epochs"]
    steps_total = epochs * ((len(data) + bs - 1) // bs)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: max(0.0, 1.0 - s / max(1, steps_total)))
    gen = random.Random(seed)

    loss_csv = cfg["loss_csv"] if not a.subset else cfg["loss_csv"].replace(".csv", f"_subset{a.subset}.csv")
    os.makedirs(os.path.dirname(loss_csv) or ".", exist_ok=True)
    with open(loss_csv, "w", newline="") as f:
        csv.writer(f).writerow(["epoch", "train_loss"])

    for epoch in range(1, epochs + 1):
        order = list(range(len(data)))
        gen.shuffle(order)
        total, tokens = 0.0, 0
        for s in range(0, len(order), bs):
            ids, labels, attn = collate([data[i] for i in order[s:s + bs]], tok.pad_token_id)
            out = model(input_ids=torch.tensor(ids), attention_mask=torch.tensor(attn), labels=torch.tensor(labels))
            n = sum(1 for lab in labels for t in lab[1:] if t != -100)  # tokens that carry loss (after the shift)
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            total += out.loss.item() * n
            tokens += n
        mean = total / max(1, tokens)
        print(f"epoch {epoch}/{epochs}  loss {mean:.4f}")
        with open(loss_csv, "a", newline="") as f:
            csv.writer(f).writerow([epoch, f"{mean:.6f}"])

    out_dir = os.path.join("artifacts", cfg["version"] + ("_subset" if a.subset else ""))
    os.makedirs(out_dir, exist_ok=True)
    model.save_pretrained(out_dir, safe_serialization=True)
    tok.save_pretrained(out_dir)
    json.dump({"version": cfg["version"], "base_model": cfg["model_name"], "records": len(rows),
               "config": {k: v for k, v in cfg.items() if k != "libraries"},
               "installed": {"torch": torch.__version__, "transformers": transformers.__version__}},
              open(os.path.join(out_dir, "version_info.json"), "w"), indent=2)

    # One archive of the model files = the GitHub Release asset; model.sha256 is the checksum of that archive.
    archive = os.path.join("artifacts", f"model-{cfg['version']}{'_subset' if a.subset else ''}.tar.gz")
    with tarfile.open(archive, "w:gz") as tar:
        for name in sorted(os.listdir(out_dir)):
            if name != "model.sha256":
                tar.add(os.path.join(out_dir, name), arcname=name)
    digest = sha256_file(archive)
    open(os.path.join(out_dir, "model.sha256"), "w").write(f"{digest}  {os.path.basename(archive)}\n")
    print(f"saved {out_dir}; {os.path.basename(archive)} sha256 {digest}")


if __name__ == "__main__":
    main()
