# Cloud Computing Mini Project: Distilled command parser on a local Kubernetes cloud

**GitHub repository:** https://github.com/YOUR_GITHUB_USER/cloud-cmd-parser   (replace with your link)
**Model release (weights, tokenizer, checksums):** https://github.com/YOUR_GITHUB_USER/cloud-cmd-parser/releases/tag/model-v1
**Final submission tag:** `final`

Teacher `phi3.5` (Ollama, temperature 0, seed 42) -> sequence-level distillation -> `EleutherAI/pythia-70m` -> FastAPI service
in a container -> k3d (k3s) cluster with SeaweedFS object storage, Traefik ingress and an HPA.

## Prerequisites
Docker, [k3d](https://k3d.io), kubectl, make, python3 (3.11+), git, [Ollama](https://ollama.com) with `ollama pull phi3.5`, `gh` (only to publish releases).
On Windows use **WSL2** (Docker Desktop with WSL integration) and run everything inside the WSL shell.
Edit `REPO` at the top of the `Makefile` to your `owner/name`.

## Build and deploy from a fresh clone (3 commands)
```bash
git clone https://github.com/YOUR_GITHUB_USER/cloud-cmd-parser && cd cloud-cmd-parser
make up        # venv, k3d cluster, SeaweedFS, buckets, models from the GitHub Release, images, app deployment
curl -s -X POST localhost:8080/parse -H 'content-type: application/json' -d '{"text":"what is the weather in london"}' -i
```
Tear down: `make down` (deletes the cluster). Credentials are generated into `.secrets/` (git-ignored) and loaded as Kubernetes Secrets.

## Task by task
| Task | Command(s) |
|---|---|
| 1. Cluster + storage + labelling | `make cluster secrets storage buckets images`; start Ollama with `OLLAMA_HOST=0.0.0.0 ollama serve`; `make pipeline` (2 parallel workers in namespace `pipeline`); `make clean-data` -> `datasets/v1/train.jsonl` + `train.sha256` |
| 2. Training | `make fetch-train`; `make train SUBSET=50` (smoke test); `make train` (v1); `make train CONFIG=training/config_v2.yaml` (v2); `make publish-model V=v1`, `V=v2`; `make release V=v1` |
| 2. Evaluation | `python evaluate/run_teacher.py`; `python evaluate/run_student.py --model EleutherAI/pythia-70m --out results/base_predictions.jsonl`; `make eval`; `python tools/score.py ...` |
| 3. Container | `docker build -f service/Dockerfile -t cmdparser:1.0 .`; `docker run --cpus=1 --memory=1g -e ... cmdparser:1.0`; `docker stats` for peak memory |
| 4. Kubernetes | `make deploy`; `make hpa-off` before the two-replica load-balancing run, `make hpa-on` after; `scripts/rolling_and_recovery.sh rolling|rollback|recovery`; `python scripts/cold_start.py 3` |
| 5. Network | `python tools/nacl_sim.py network/nacl.json network/packets_sample.jsonl --check`; see `network/subnets.md` |
| 6. CI/CD | `.github/workflows/ci.yml` (lint+gitleaks -> unit tests -> model evaluation -> quality gate); `make lint test scan` |
| 7. Performance | `scripts/loadtest.sh 2m results/loadtest`; `python scripts/report_metrics.py --replicas 2` |

## Layout
`cluster/` k3d config - `k8s/` manifests - `worker/` sharded teacher worker + `clean.py` - `training/` config + `train.py` - `service/` FastAPI app + Dockerfile -
`evaluate/` scoring runners - `network/` subnets + NACL - `prompts/` teacher prompt - `tests/` unit tests - `scripts/` helpers - `results/` evidence - `report/` report - `AI_USE.md`.

Model weights are **not** in Git: they live in the `models` bucket and as GitHub Release assets (`model-v1.tar.gz`, `model-v1.sha256`).
Data: commands from SLURP (Bastianelli et al., EMNLP 2020), CC BY 4.0.
