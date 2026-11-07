#!/usr/bin/env bash
# Standard load test through the Ingress, with kubectl top sampling alongside. Usage: scripts/loadtest.sh [RUN_TIME] [CSV_PREFIX]
set -uo pipefail
RUN_TIME="${1:-2m}"; PREFIX="${2:-results/loadtest}"
mkdir -p results
( while true; do date +%T; kubectl -n app top pods --no-headers; sleep 10; done ) > "${PREFIX}_top_pods.txt" 2>&1 &
TOP=$!
locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time "$RUN_TIME" \
  --host http://localhost:8080 --csv "$PREFIX" 2>&1 | tee "${PREFIX}_console.txt"
kill $TOP 2>/dev/null
exit 0   # Locust exits 1 when any request failed; that is normal, read the numbers
