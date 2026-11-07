SHELL := /bin/bash
# Edit REPO to your GitHub "owner/name" (used to fetch the model release on a fresh clone).
REPO        ?= YOUR_GITHUB_USER/cloud-cmd-parser
RELEASE_URL ?= https://github.com/$(REPO)/releases/download
CLUSTER     := cmdparser
VENV        := .venv
PY          := $(VENV)/bin/python
CONFIG      ?= training/config.yaml
SUBSET      ?=

-include .secrets/s3.env
export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
export S3_ENDPOINT ?= http://localhost:8333

.PHONY: up down deps cluster secrets storage buckets seed images deploy hpa-on hpa-off test lint train fetch-train \
        publish-model release pipeline clean-data eval loadtest scan

## ---- whole system: `make up` from a fresh clone (needs docker, k3d, kubectl, make, python3) ----
up: deps cluster secrets storage buckets seed images deploy
	@echo "Ready: curl -X POST localhost:8080/parse -H 'content-type: application/json' -d '{\"text\":\"what is the weather in london\"}'"

down:
	k3d cluster delete $(CLUSTER)

deps:
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PY) -m pip install -q -r requirements-dev.txt

cluster:
	k3d cluster list $(CLUSTER) >/dev/null 2>&1 || k3d cluster create --config cluster/k3d.yaml
	kubectl apply -f k8s/00-namespaces.yaml

secrets:
	scripts/gen-secrets.sh

storage:
	kubectl apply -f k8s/data/seaweedfs.yaml
	kubectl -n data rollout status deployment/seaweedfs --timeout=300s

buckets:
	$(PY) scripts/s3tool.py mkbuckets
	$(PY) scripts/s3tool.py put datasets commands_pool.jsonl data/commands_pool.jsonl

# Model weights: from artifacts/ if trained locally, otherwise from the GitHub Release (checksum verified).
seed:
	@for v in v1 v2; do \
	  if [ -d artifacts/$$v ]; then $(PY) scripts/s3tool.py publish-model $$v; \
	  else $(PY) scripts/s3tool.py publish-model $$v --release-url $(RELEASE_URL)/model-$$v/model-$$v.tar.gz; fi; done

images:
	docker build -f service/Dockerfile -t cmdparser:1.0 .
	docker build -f worker/Dockerfile -t cmdparser-worker:1.0 .
	k3d image import cmdparser:1.0 cmdparser-worker:1.0 -c $(CLUSTER)

deploy:
	kubectl apply -f k8s/app/deployment.yaml -f k8s/app/service-ingress-hpa.yaml
	kubectl -n app rollout status deployment/cmdparser --timeout=600s

# For the "exactly two Ready replicas" load-balancing run, switch the autoscaler off, then back on.
hpa-off:
	kubectl -n app delete hpa cmdparser --ignore-not-found
	kubectl -n app scale deployment/cmdparser --replicas=2
hpa-on:
	kubectl apply -f k8s/app/service-ingress-hpa.yaml

## ---- Task 1: teacher labelling (Ollama phi3.5 must be running on the host with OLLAMA_HOST=0.0.0.0) ----
pipeline:
	kubectl apply -f k8s/pipeline/teacher-job.yaml
	kubectl -n pipeline wait --for=condition=complete job/teacher-labelling --timeout=24h
clean-data:
	$(PY) worker/clean.py

## ---- Task 2: training ----
fetch-train:
	mkdir -p data && $(PY) scripts/s3tool.py get datasets v1/train.jsonl data/train.jsonl
train:
	$(PY) training/train.py --config $(CONFIG) $(if $(SUBSET),--subset $(SUBSET),)
publish-model:
	$(PY) scripts/s3tool.py publish-model $(V)
release:
	gh release create model-$(V) artifacts/model-$(V).tar.gz "artifacts/$(V)/model.sha256#model-$(V).sha256" --title "Model $(V)" --notes "Pythia-70M distilled from phi3.5 (version $(V))"

## ---- quality ----
lint:
	$(PY) -m ruff check .
test:
	$(PY) -m pytest -q
eval:
	$(PY) evaluate/run_student.py --model artifacts/v1 --out results/student_predictions.jsonl
	$(PY) tools/score.py results/student_predictions.jsonl data/validation.jsonl --out results/student_validation.json
loadtest:
	scripts/loadtest.sh 2m results/loadtest
scan:
	gitleaks detect --source . --no-banner
