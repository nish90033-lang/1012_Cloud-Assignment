#!/usr/bin/env bash
# Generates S3 credentials locally (never committed: .secrets/ is git-ignored) and loads them into the cluster as Secrets.
set -euo pipefail
mkdir -p .secrets
if [ ! -f .secrets/s3.env ]; then
  AK="cp$(python3 -c 'import secrets;print(secrets.token_hex(8))')"
  SK="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
  printf 'AWS_ACCESS_KEY_ID=%s\nAWS_SECRET_ACCESS_KEY=%s\n' "$AK" "$SK" > .secrets/s3.env
  chmod 600 .secrets/s3.env
fi
# shellcheck disable=SC1091
source .secrets/s3.env
cat > .secrets/s3.json <<JSON
{"identities":[{"name":"admin","credentials":[{"accessKey":"$AWS_ACCESS_KEY_ID","secretKey":"$AWS_SECRET_ACCESS_KEY"}],"actions":["Admin","Read","Write","List","Tagging"]}]}
JSON
kubectl -n data create secret generic seaweedfs-s3-config --from-file=s3.json=.secrets/s3.json --dry-run=client -o yaml | kubectl apply -f -
for ns in pipeline app; do
  kubectl -n "$ns" create secret generic s3-credentials \
    --from-literal=AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
    --from-literal=AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" --dry-run=client -o yaml | kubectl apply -f -
done
echo "secrets applied"
