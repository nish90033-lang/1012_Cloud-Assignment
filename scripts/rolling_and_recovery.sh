#!/usr/bin/env bash
# Task 4 steps 5 and 6. Start the load test in another terminal first with a longer run time, e.g.
#   scripts/loadtest.sh 6m results/rolling
# then run:  scripts/rolling_and_recovery.sh rolling   |   rollback   |   recovery
set -euo pipefail
case "${1:-}" in
  rolling)
    kubectl -n app set env deployment/cmdparser MODEL_VERSION=v2 MODEL_URI=s3://models/v2/
    kubectl -n app rollout status deployment/cmdparser --timeout=600s ;;
  rollback)
    kubectl -n app rollout undo deployment/cmdparser
    kubectl -n app rollout status deployment/cmdparser --timeout=600s ;;
  recovery)
    kubectl -n app get pods -l app=cmdparser
    POD=$(kubectl -n app get pods -l app=cmdparser -o jsonpath='{.items[0].metadata.name}')
    kubectl -n app delete pod "$POD" --wait=false
    for i in $(seq 1 30); do kubectl -n app get pods -l app=cmdparser --no-headers; echo ---; sleep 5; done ;;
  *) echo "usage: $0 rolling|rollback|recovery"; exit 2 ;;
esac
