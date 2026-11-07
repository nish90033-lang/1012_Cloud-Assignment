# Cloud Computing Mini Project: Distilled Command Parser

**Course:** CS3081 Cloud Computing
**Student:** Nishant Suryavanshi
**Roll Number:** 230101012
**Institution:** IIIT Manipur
**Repository:** https://github.com/nish90033-lang/1012_Cloud-Assignment
**Final submission tag:** `final`

## 1. Overview

A cloud-native natural-language command parser built using teacher-generated training data and a distilled EleutherAI Pythia-70M student model.

The system includes distributed teacher labelling, dataset cleaning, model training and evaluation, a FastAPI inference service, Docker packaging, Kubernetes orchestration, S3-compatible object storage, network segmentation, CI/CD, and performance evaluation.

### Architecture

```text
Ollama phi3.5 Teacher
        |
        v
Kubernetes Teacher Workers
        |
        v
Dataset Cleaning and Recovery
        |
        v
Pythia-70M Student Training
        |
        v
Model Artifacts
        |
        v
GitHub Releases
        |
        v
SeaweedFS S3 Storage
        |
        v
FastAPI Inference Service
        |
        v
Kubernetes Deployment + HPA
        |
        v
Ingress and JSON Response

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Teacher model | Ollama phi3.5 |
| Student model | EleutherAI Pythia-70M |
| Training | Python, PyTorch, Transformers |
| API | FastAPI, Uvicorn |
| Containerization | Docker |
| Orchestration | Kubernetes, k3d |
| Object storage | SeaweedFS S3 |
| Ingress | Traefik |
| Load testing | Locust |
| CI/CD | GitHub Actions |
| Quality checks | Ruff, pytest, Gitleaks |

## 3. Prerequisites

- Docker, k3d, kubectl, Make and Git
- Python 3.11
- Internet access for dependencies and model downloads
- Ollama with phi3.5 for reproducing teacher labelling

For Windows, use Ubuntu through WSL2 with Docker Desktop integration.

## 4. Fresh Clone: Build and Deploy

```bash
git clone https://github.com/nish90033-lang/1012_Cloud-Assignment.git
cd 1012_Cloud-Assignment
make up
