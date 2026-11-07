# AI use statement

**Edit this file so it describes what you actually did and checked.** Draft based on how this repository was produced:

## Tools
- Claude (Anthropic) - generated the first version of the repository scaffolding: worker, `clean.py`, training script, FastAPI service,
  Dockerfile, Kubernetes manifests, Makefile, CI workflow, unit tests, subnet table and NACL, report and reflection drafts.
- (Add anything else you used: Copilot, ChatGPT, documentation, classmates' discussion.)

## How the output was checked
- Run locally in the sandbox where it was written: `ruff check .`, `pytest` (19 tests), `tools/nacl_sim.py --check` (6/6), `clean.py` on synthetic shards
  with `sha256sum -c`, YAML parsing of every manifest.
- NOT run by the AI (no Docker, k3d, Ollama, PyTorch or network access to Hugging Face in its sandbox): the teacher run, training, image build,
  all Kubernetes behaviour and all load tests. **Every measured number in the report must come from your own runs.**
- Things to verify by hand yourself: SeaweedFS flags and S3 config (`k8s/data/seaweedfs.yaml`), `host.k3d.internal` reachability of Ollama,
  Indexed Job env wiring, pinned package versions installing together, the image size (`docker images`), the subnet arithmetic (re-derive it), and every claim in the report.
- Corrections made after review: (list bugs you found in the generated code and how you fixed them).
