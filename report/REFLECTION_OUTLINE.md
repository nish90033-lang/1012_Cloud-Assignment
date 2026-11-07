# Handwritten reflection - outline (3 pages, handwrite and scan as <roll_number>.pdf)

The reflection must be in your own words and handwriting. This outline lists what to cover; fill the brackets from what actually happened to you.
Put at the top: name, roll number, GitHub link.

1. What I learnt: how sequence-level distillation works (student copies the teacher's outputs) and why logits were not available; [what surprised you about the student's quality];
   how a k3d cluster, Services, probes, HPA and rolling updates behave in practice; why a stateless NACL needs reply rules and rule ordering.
2. Challenges: [e.g. teacher labelling time on CPU; Ollama reachable from the cluster; image size; OOM at 1 GiB; probes killing a Pod that was still downloading]. Write the real ones.
3. How I solved them: [what you tried, what finally worked].
4. Findings / observations: [your measured numbers: validity, full-frame vs teacher, p95, cold start, load balance].
5. What could be better: [more data, quantisation, multi-node, caching the model, logit distillation].
6. How I used AI and how I checked it (short; see AI_USE.md).
