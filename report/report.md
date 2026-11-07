---
title: "Distilling and Deploying a Command-Parsing LM on a Local Cloud"
subtitle: "CS3081 Cloud Computing - Mini Project report (DRAFT: every ‹TBD› must be replaced by a number you measured)"
author: "Name: ‹your name›  -  Roll number: ‹roll number›  -  Repo: https://github.com/YOUR_GITHUB_USER/cloud-cmd-parser"
---

**Convention.** *Measured* = copied from a file in `results/`. *Assumed* = a design choice or estimate, labelled as such.

# 1. Architecture
Laptop: Ollama serves `phi3.5` (teacher). k3d cluster `cmdparser` (1 server node): namespace `data` runs SeaweedFS (S3 API, buckets `datasets`, `models`);
`pipeline` runs two parallel labelling workers; `app` runs the inference Deployment behind a Service, a Traefik Ingress (`/parse`, host port 8080) and an HPA.
Flow: `commands_pool.jsonl` -> workers -> `datasets/teacher/shard-i.jsonl` -> `clean.py` -> `datasets/v1/train.jsonl` -> `train.py` (laptop, CPU) ->
`models/v1|v2/` and GitHub Release -> service downloads the model at start-up. Credentials are Kubernetes Secrets generated locally into a git-ignored folder.

# 2. Task 1 - Object storage and parallel labelling
**Setup.** Cluster from `cluster/k3d.yaml`; SeaweedFS in `data`; prompt in `prompts/teacher_prompt.txt` (instructions, schema, slot rules, five examples; sent through
Ollama `/api/generate`, temperature 0, seed 42). Teacher location: ‹laptop / in-cluster›.
**Sharding.** The worker reads `SHARD_INDEX` and `SHARD_COUNT` and handles line numbers `n` with `n mod SHARD_COUNT = SHARD_INDEX`. The residue classes partition the
line numbers, so every command belongs to exactly one shard (no gaps, no repeats) with no coordination between workers; shards differ in size by at most one.
An Indexed Job (`completions=2, parallelism=2`) gives each Pod its index. Each worker writes its own object (no write conflicts), uploads a checkpoint every 25 records and resumes
from its object after a crash. Limitation: both workers share one Ollama on one CPU, so wall-clock speed-up is ‹TBD› (compute-bound, not 2x).
**Cleaning.** Reasons are applied in order (a)-(d), each record counted once; duplicates are then collapsed among the survivors keeping the smallest id.

| Input | (a) not JSON | (b) wrong keys | (c) bad intent | (d) slot not in command | Duplicates | Kept |
|---|---|---|---|---|---|---|
| 3000 | ‹TBD› | ‹TBD› | ‹TBD› | ‹TBD› | ‹TBD› | ‹TBD› |

Check: input = a+b+c+d+duplicates+kept (asserted in code). `train.sha256` = ‹hash›; re-running `clean.py` reproduces it ‹yes/no›.

# 3. Task 2 - Training the student
Sequence-level distillation: Pythia-70M is fine-tuned with next-token cross-entropy on `Command: <cmd>\nJSON: <teacher reply><eos>` (loss on the reply tokens only), first 1,500 cleaned records.
`training/config.yaml`: seed 42, lr 1e-4, batch 16, 3 epochs, max length 128, library versions pinned. Loss per epoch (`training/loss_v1.csv`): ‹TBD›. v2: seed 7, 4 epochs (`config_v2.yaml`).
Artefacts: `models/v1`, `models/v2`; Release asset `model-v1.tar.gz`; SHA-256 ‹hash› matches `model.sha256`: ‹yes/no›.

| Model (validation, 100 commands, %) | json_validity | intent | date | time | place | full_frame |
|---|---|---|---|---|---|---|
| Teacher phi3.5 | ‹TBD› | ‹TBD› | ‹TBD› | ‹TBD› | ‹TBD› | ‹TBD› |
| Pythia-70M untrained | ‹TBD› | ‹TBD› | ‹TBD› | ‹TBD› | ‹TBD› | ‹TBD› |
| Student v1 | ‹TBD› | ‹TBD› | ‹TBD› | ‹TBD› | ‹TBD› | ‹TBD› |

Discussion: ‹what changed after distillation; where the student is still wrong; how it compares with the teacher - write from your own results›.
Suitability of Pythia-70M: very small English decoder, Apache-2.0, fast on CPU, but little capacity for exact copying of slot spans and no instruction tuning.

**Sequence-level vs logit-based distillation.** Sequence-level distillation trains the student on the teacher's *generated outputs* (hard targets, one sampled/decoded sequence per input).
Logit-based distillation trains the student to match the teacher's *token-level output probability distribution* (soft targets, e.g. KL divergence over the vocabulary).
It is not possible here because Ollama returns text, not full-vocabulary logits, and phi3.5 and Pythia use different tokenizers/vocabularies, so distributions cannot be aligned token by token.
Limitation of what was done: the student only sees the teacher's *single* answer, so teacher mistakes (some slip through cleaning, since the cleaner checks form, not correctness) are copied, and 1,500 examples cover little of the phrase variety; ‹add one measured example›.

# 4. Task 3 - The inference service
FastAPI on port 8000: `POST /parse` (200 + the four-key object only; headers `X-Model-Version`, `X-Served-By`), `GET /healthz` (alive), `GET /readyz` (503 until loaded).
Model download runs in a background thread so `/healthz` answers while `/readyz` is 503. Config: `MODEL_URI, MODEL_VERSION, S3_ENDPOINT, MAX_NEW_TOKENS` (+ `FAULT_INJECT`); credentials from a Secret.
Every output is validated against `schema.json`; invalid -> 500 `{"error":"invalid_model_output"}`. Unit tests cover readiness, headers, fault injection and four malformed outputs.
Image: `python:3.11.9-slim`, CPU-only torch wheel, all versions pinned, no weights; size ‹TBD› GB (limit 2). Limits test (`docker run --cpus=1 --memory=1g`, 50 sequential requests): ‹completed / OOM›, peak memory ‹TBD› MiB (`docker stats`, evidence in `results/`).

# 5. Task 4 - Kubernetes deployment, scaling, reliability
Namespace `app`: Deployment (2 replicas; requests 500m/512Mi, limits 1 CPU/1Gi), Service, Ingress, liveness `/healthz`, readiness `/readyz`; RollingUpdate `maxSurge 1, maxUnavailable 0`.
HPA: min 1, max 2, CPU 70% (of the *request*, i.e. 350m). Limitations of the local cluster: one node, so no real fault tolerance across machines; one laptop's CPU is shared by Pods, load generator and Ollama;
metrics-server samples every ~15-60 s so scaling reacts slowly; HPA and a fixed `replicas: 2` fight each other (the HPA wins), so the 2-replica test disables it.

| Check | Result |
|---|---|
| No ready endpoints while the model loads | ‹TBD› |
| Scale 1 -> 2 under load and back to 1 | ‹evidence› |
| Rolling update v1 -> v2: failed / total requests | ‹TBD› (limit 0.5%) |
| After `kubectl rollout undo`: `X-Model-Version` | ‹v1?› |
| Pod deleted under load: replicas restored; failed requests | ‹TBD›; ‹TBD› % (limit 2%) |
| Cold start, 3 runs (s) and median | ‹TBD›, ‹TBD›, ‹TBD›; median ‹TBD› (logs show the S3 download) |
| Load balancing, requests per replica | ‹replica A: n (x%)›, ‹replica B: n (x%)› |

# 6. Task 5 - Subnetting and NACL
Allocation (largest first, from 10.20.0.0; full working in `network/subnets.md`):

| Subnet | Network/prefix | Usable range | Broadcast | Usable hosts |
|---|---|---|---|---|
| app (1000) | 10.20.0.0/22 | 10.20.0.1 - 10.20.3.254 | 10.20.3.255 | 1022 |
| public (250) | 10.20.4.0/24 | 10.20.4.1 - 10.20.4.254 | 10.20.4.255 | 254 |
| data (100) | 10.20.5.0/25 | 10.20.5.1 - 10.20.5.126 | 10.20.5.127 | 126 |
| management (20) | 10.20.5.128/27 | 10.20.5.129 - 10.20.5.158 | 10.20.5.159 | 30 |

NACL (`network/nacl.json`) - inbound: 100 deny 198.51.100.0/24 (all); 110 allow tcp 80; 120 allow tcp 443; 130 allow tcp 22 from 10.20.5.128/27; 140 allow tcp 1024-65535 from 10.20.0.0/22 (replies from app).
Outbound: 100 allow tcp 8000 to 10.20.0.0/22; 110 allow tcp 1024-65535 to 0.0.0.0/0 (replies to clients). `nacl_sim.py --check`: 6/6.
A NACL is stateless: it keeps no record of connections, so a reply is just another packet that needs its own allow rule on the ephemeral-port range. Rules run from the lowest number and the first match wins,
so the deny for 198.51.100.0/24 must be numbered below the allow rules for 80/443, otherwise those allows match first and the abusive range gets through.
Design note: because the specified ephemeral range (1024-65535) contains 8000, the reply rule also lets port 8000 leave to non-app addresses; a stateless rule cannot tell a reply from a new connection.

# 7. Task 6 - Reproducibility, testing, CI/CD
`make up` builds and deploys from a fresh clone (verified on ‹date/machine›); `make down` deletes the cluster. Workflow `ci.yml`: lint (ruff) + gitleaks -> unit tests (19) ->
model evaluation (model from the GitHub Release, `score.py` on `validation.jsonl`) -> quality gate (`--min-validity 95`). Failed gate with the untrained model: ‹link to failed run›.
Passing run with the trained model: ‹link›. Secret scan result: ‹no leaks›. AI use: `AI_USE.md`.

# 8. Task 7 - Performance, cost, SLO, review
Standard load test (4 users, 2 min, through the Ingress, 2 replicas): requests ‹n›, p50 ‹ms›, p95 ‹ms›, throughput ‹rps›, error rate ‹%›. `kubectl top pods`: ‹pod: CPU, memory›. Cold start (Task 4): ‹median s›.
**Cost** (rate card: 3.50 INR per vCPU-hour, 0.45 INR per GiB-hour; assumption: each replica billed for its limits, 1 vCPU + 1 GiB):
per replica per hour = 1 x 3.50 + 1 x 0.45 = 3.95 INR; 2 replicas = 7.90 INR/h; requests per hour = ‹rps› x 3600 = ‹n›;
cost per 1,000 requests = 7.90 / ‹n› x 1000 = **‹TBD› INR** (`scripts/report_metrics.py`).
**SLO:** 99% of requests succeed within one load-test run. Error budget = 1% x ‹N› = ‹B› requests; failures ‹F›; budget used ‹F/B %›; SLO ‹met / missed›.

| Component | Evidence (measured) | Limitation found | Improvement |
|---|---|---|---|
| Data and storage | ‹kept records / 3000; checksum reproduced› | single-pod SeaweedFS, no replication | replicate volumes, versioned datasets |
| Model quality | ‹full_frame student vs teacher› | 1,500 teacher-labelled examples, teacher errors copied | more data, filter by agreement, logit KD with a shared-vocabulary teacher |
| Latency and throughput | ‹p50, p95, rps› | one thread per Pod, batch size 1 | batching, quantisation (int8), ONNX |
| Resource utilisation | ‹top: CPU/mem per Pod› | requests/limits set by guess | tune from measurements, use VPA |
| Reliability and recovery | ‹rolling %, recovery %, cold start s› | single node, cold start downloads the model | multi-node cluster, model cache on a volume |
| Security and cost | ‹gitleaks: 0 findings; cost per 1,000 req› | HTTP inside cluster, one shared S3 identity | TLS, per-service credentials, NetworkPolicies |

# References
Kim & Rush, Sequence-Level Knowledge Distillation, EMNLP 2016. Bastianelli et al., SLURP, EMNLP 2020 (CC BY 4.0). EleutherAI Pythia-70M model card.
